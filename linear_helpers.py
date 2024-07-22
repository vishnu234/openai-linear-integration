from gql import gql, Client
from typing import Optional

# TODO(vcd): Maybe we can use GPT or some basic string parsing 
# to get the team id from a list of teams in linear?
def list_issues(client: Client, team_id: str):
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
        """.format(team_id=team_id)
    )
    result = client.execute(query)
    return result

def create_issue(client: Client, title: str, description: str, team_id: str):
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

def edit_issue(client: Client, issue_id: str, new_title: Optional[str] = None, new_description: Optional[str] = None):
    issues = list_issues(client)
    found_issue = False
    for issue in issues:
        if issue.id == issue_id:
            found_issue = True
            if new_title is None:
                new_title = issue.title
                new_description = issue.description
    if not found_issue:
        return None
    
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
            new_title=new_title,
            new_description=new_description,
        )
    )
    result = client.execute(query)
    return result

# TODO(vcd): For a production app I would implement some sort of test cases
