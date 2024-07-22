from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

from constants import LINEAR_KEY, LINEAR_TEAM_ID

def user_info_example():
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql(
        """
        query Me {
            viewer {
                id
                name
                email
            }
        }
        """
    )
    result = client.execute(query)
    print(result)


def list_teams():
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql(
        """
        query Teams {
            teams {
                nodes {
                    id
                    name
                }
            }
        }
        """
    )
    result = client.execute(query)
    print(result)


def list_team_issues():
    TEST_TEAM_ID = "a409ee5a-1f47-4e5f-bf16-332272fefacf"
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
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
                state {{
                  id
                  name
                }}
            }}
            }}
        }}
        }}
        """.format(
            team_id=TEST_TEAM_ID
        )
    )
    result = client.execute(query)
    print(result)

def add_issue():
    TEST_TEAM_ID = "a409ee5a-1f47-4e5f-bf16-332272fefacf"

    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
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
            title="Can't change password",
            description="User can't change the password of their account",
            linear_team_id=TEST_TEAM_ID,
        )
    )
    result = client.execute(query)
    print(result)

def edit_existing_issue():
    TEST_TEAM_ID = "a409ee5a-1f47-4e5f-bf16-332272fefacf"

    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
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
            issue_id="cabbaabd-384d-4b0b-80ad-cdebfdaf3c89",
            new_title="Edited Test Issue",
            new_description="Edited test description",
        )
    )
    result = client.execute(query)
    print(result)

if __name__ == "__main__":
    add_issue()