import git
import re
import os
import requests
import tempfile


REL_REGEX = re.compile("rel=\\\"([A-z]+)\\\"")


def github_request(access_key, url, paginate=False, method='GET'):
    headers = {"Authorization": "token {}".format(access_key)}
    if not paginate:
        response = requests.request(
            method, url, headers=headers)
        return response.json()
    else:
        result = []
        while url is not None:
            response = requests.request(
                method, url, headers=headers)
            if "link" in response.headers:
                links = parse_link_header(response.headers["link"])
                next_url = [link["url"]
                            for link in links if link["rel"] == "next"]
                if len(next_url) > 0:
                    url = next_url[0]
                else:
                    url = None
            else:
                url = None
            result += response.json()
        return result


def parse_link_header(value):
    # Eg:
    # '<https://api.github.com/organizations/xxx/repos?per_page=100&page=2>; rel="next", <https://api.github.com/organizations/xxx/repos?per_page=100&page=2>; rel="last"'
    links = [link.strip().split(";") for link in value.split(",")]
    parsed_links = []
    for link in links:
        url = link[0][1:-1]
        # Assuming it matches
        rel = REL_REGEX.match(link[1].strip()).groups()[0]
        parsed_links.append({
            "url": url, "rel": rel
        })
    return parsed_links


def get_orgs(access_key):
    url = "https://api.github.com/user/orgs"
    response = github_request(access_key, url, paginate=True)
    return [org["login"] for org in response]


def get_org_repos(access_key, org):
    url = "https://api.github.com/orgs/{}/repos?per_page=100".format(org)
    return github_request(access_key, url, True)


def git_credentials():

    (handle, path) = tempfile.mkstemp()
    handle.write("#!/bin/sh")


def main():
    # Provide this in environment!
    access_key = os.environ["ACCESS_KEY"].rstrip()
    output_base = os.environ.get(
        "OUTPUT_BASE", os.path.join(os.getcwd(), "repos"))

    orgs = get_orgs(access_key)
    print("Organisations: {}".format(", ".join(orgs)))

    for org in orgs:
        print("Repos for {}".format(org))
        for repo in get_org_repos(access_key, org):
            output_path = os.path.join(
                output_base, "/".join([org, repo['name']]))
            if os.path.isdir(output_path):
                print("Pulling: {} in {}".format(
                    repo["full_name"], output_path))
                repo = git.Repo(output_path)
                origin = repo.remote()
                origin.pull()
            else:
                print("Cloning: {} to {}".format(
                    repo["full_name"], output_path))
                git.Repo.clone_from(
                    repo['ssh_url'], output_path, **{"recurse-submodules": True})


if __name__ == "__main__":
    main()
