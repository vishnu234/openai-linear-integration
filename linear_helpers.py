from gql import gql, Client
from typing import Optional, Dict


def get_issue(client: Client, issue_id: str) -> Dict:
    query = gql(
        """
        query Issue {{
            issue(id: "{issue_id}") {{
                id
                title
                description
            }}
        }}
        """.format(
            issue_id=issue_id
        )
    )
    result = client.execute(query)
    return result


# TODO(vcd): Maybe we can use GPT or some basic string parsing
# to get the team id from a list of teams in linear?
def list_issues(client: Client, team_id: str) -> Dict:
    query = gql(
        """
        query Team {{
        team(id: "{team_id}") {{
            id
            name

            issues {{
            nodes {{
                id
                title
                description
                assignee {{
                id
                name
                }}
                createdAt
                archivedAt
            }}
            }}
        }}
        }}
        """.format(
            team_id=team_id
        )
    )
    result = client.execute(query)
    return result


def create_issue(client: Client, title: str, description: str, team_id: str) -> Dict:
    query = gql(
        """
        mutation IssueCreate {{
            issueCreate(
                input: {{
                title: "{title}"
                description: "{description}"
                teamId: "{linear_team_id}"
                }}
            ) {{
                success
                issue {{
                id
                title
                description
                }}
            }}
        }}
        """.format(
            title=title,
            description=description,
            linear_team_id=team_id,
        )
    )
    result = client.execute(query)
    return result


def edit_issue(
    client: Client,
    issue_id: str,
    new_title: Optional[str] = None,
    new_description: Optional[str] = None,
) -> Dict:
    issue = get_issue(client, issue_id)["issue"]
    if new_title is None:
        new_title = issue["title"]
    if new_description is None:
        new_description = issue["description"]

    # Replace double quotes with single quotes to avoid string
    # parsing errors in GraphQL Query
    query = gql(
        """
        mutation IssueUpdate {{
        issueUpdate(
            id: "{issue_id}",
            input: {{
            title: "{new_title}"
            description: "{new_description}"
            }}
        ) {{
            success
            issue {{
            id
            title
            description
            }}
        }}
        }}
        """.format(
            issue_id=issue_id,
            new_title=new_title.replace('"', "'"),
            new_description=new_description.replace('"', "'"),
        )
    )
    result = client.execute(query)
    return result
