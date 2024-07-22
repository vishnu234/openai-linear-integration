from openai import OpenAI
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import json
from typing import List, Optional

from linear_helpers import list_issues, create_issue, edit_issue
from constants import LINEAR_KEY, LINEAR_TEAM_ID, OPENAI_KEY

# TODO: Add types for return values for functions
# TODO: Should we pull out GPT API calls into a separate gpt_helpers.py file?
# TODO: Should we add a status id to new issues
# TODO: How can we separate BRs and FRs? Should we have one team for FRs and one team for BRs?
# TODO: How should we append to existing issue vs create new issue? Iterate over all existing issues?

def create_linear_issue(title: str, description: str, linear_client: Client):
    return create_issue(
        client=linear_client,
        title=title,
        description=description,
        team_id=LINEAR_TEAM_ID,
    )

def edit_linear_issue(issue_id: str, new_title: Optional[str], new_description: Optional[str], linear_client: Client):
    return edit_issue(
        client=linear_client,
        issue_id=issue_id,
        new_title=new_title,
        new_description=new_description,
    )

def handle_bug_report_or_feature_request(title: str, description: str, openai_client: OpenAI):
    """
    Function to handle bug reports or feature requests
    This function will check if an existing task exists.
    If it does, the description and title of the task will get updated.
    If it doesn't, then a new task will be created
    """
    gpt_function_tools = [
        {
            "type": "function",
            "function": {
                "name": "edit_linear_issue",
                "description": "Adds to the description of an existing issue in linear using the GraphQL API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "new_title": {
                            "type": "string",
                            "description": "New title for the issue. This title summarizes the original issue and the new related issue.",
                        },
                        "new_description": {
                            "type": "string",
                            "description": "New description for the issue. This description contains information describing the original issue, and information describing the new related issue.",
                        },
                    },
                },
            },
        },
    ]
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    linear_client = Client(transport=transport, fetch_schema_from_transport=True)
    issues = list_issues(
        client=linear_client,
        team_id=LINEAR_TEAM_ID
    )["team"]["issues"]["nodes"]
    for existing_issue in issues:
        # TODO(vcd): Should we add title information to the prompt as well? 
        # Maybe some sort of evaluation suite would let us converge on the right prompt
        gpt_prompt = f"Do the original issue and new issue describe the same issue? Original Issue Description: {existing_issue['description']}. New Issue Description: {description}. If yes, please add additional useful context from the new issue to the existing issue in Linear."
        messages = [
            {
                "role": "user",
                "content": gpt_prompt,
            }
        ]
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=gpt_function_tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            available_functions = {
                "edit_linear_issue": edit_linear_issue,
            }
            tool_call_outputs = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(
                    issue_id=existing_issue["id"],
                    new_title=function_args.get("new_title"),
                    new_description=function_args.get("new_description"),
                    linear_client=linear_client,
                )
                tool_call_outputs.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
            return tool_call_outputs
    
    return [{
        "name": "create_linear_issue",
        "content": create_linear_issue(title, description, linear_client),
    }]
    

def _handle_other(_description: str):
    """ Placeholder for handling a message that isn't a bug report or feature request """
    pass

# TODO: We shouldn't to separate this from dedup'ing from existing tasks
def categorize_conversation(conversation: str):
    """

    """
    prompt = f"Does the following conversation depict a bug report, feature request, or neither?  {conversation}. If it's a bug report, can you ingest it into Linear?"
    openai_client = OpenAI(
        api_key=OPENAI_KEY,
    )
    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "handle_bug_report_or_feature_request",
                "description": "Handles a bug report or feature request by ingesting it into Linear using their GraphQL API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of a task resulting from the bug report and/or feature request described in the conversation",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the task resulting from the bug report or feature request described in the conversation",
                        },
                    },
                    "required": ["title", "description"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "handle_other",
                "description": "Handles queries that aren't bug reports or feature requests",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of the conversation that was neither a bug report nor a feature request",
                        },
                    },
                },
            },
        },
    ]
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    # Check if the model wanted to call a function
    if tool_calls:
        available_functions = {
            "handle_bug_report_or_feature_request": handle_bug_report_or_feature_request,
            "handle_other": _handle_other,
        }
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                title=function_args.get("title"),
                description=function_args.get("description"),
                openai_client=openai_client,
            )
            for tool_call_output in function_response:
                if tool_call_output["name"] == "create_linear_issue":
                    issue_dict = tool_call_output["content"]["issueCreate"]["issue"]
                    print(f"Created new linear issue for this conversation! \nID: {issue_dict['id']} \nTitle: {issue_dict['title']} \nDescription: {issue_dict['description']}")
                elif tool_call_output["name"] == "edit_linear_issue":
                    issue_dict = tool_call_output["content"]["issueUpdate"]["issue"]
                    print(f"Added information from this conversation to an existing linear issue! \nID: {issue_dict['id']} \nTitle: {issue_dict['title']} \nDescription: {issue_dict['description']}")

def test_cases():
    bug_report_1 = "[User]: 'I can't change my delivery address', [Agent]: 'Sorry for the inconvenience we will get that fixed right away'"

    feature_request_1 = "[User]: 'I would like to be able to change my delivery address', [Agent]: 'Thanks for the suggestion!'"

    general_query_1 = "[User]: 'Hi, I can't figure out how to change my delivery address', [Agent]: 'You can change it by going to Settings > User Information > Address', [User]: 'Thanks!'"

    categorize_conversation(feature_request_1)


if __name__ == "__main__":
    test_cases()