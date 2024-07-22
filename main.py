from openai import OpenAI
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
import json
from typing import List

from linear_helpers import list_issues, create_issue, edit_issue
from constants import LINEAR_KEY, LINEAR_TEAM_ID, OPENAI_KEY

# TODO: Add types for return values for functions
# TODO: Should we pull out GPT API calls into a separate gpt_helpers.py file?
# TODO: Should we add a status id to new issues
# TODO: How can we separate BRs and FRs? Should we have one team for FRs and one team for BRs?
# TODO: How should we append to existing issue vs create new issue? Iterate over all existing issues?

def create_linear_issue(title: str, description: str, linear_client: Client):
    create_issue(
        client=linear_client,
        title=title,
        description=description,
        team_id=LINEAR_TEAM_ID,
    )

def edit_linear_issue(issue_id: str, new_title: str, new_description: str, linear_client: Client):
    edit_issue(
        client=linear_client,
        issue_id=issue_id,
        title=new_title,
        description=new_description,
    )

def handle_bug_report_or_feature_request(title: str, description: str, openai_client: OpenAI, messages: List):
    """
    Function to handle bug reports or feature requests
    This function will check if an existing issue exists. If not, it will 
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
                    "required": ["title"],
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
        gpt_prompt = f"Do the original issue and new issue describe the same issue? Original Issue: {existing_issue['description']}. New Issue: {description}. If yes, please add additional useful context from the new issue to the existing issue in Linear."
        # messages.append({
        #     "role": "user",
        #     "content": gpt_prompt,
        # })
        new_messages = [
            {
                "role": "user",
                "content": gpt_prompt,
            }
        ]
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=new_messages,
            tools=gpt_function_tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            available_functions = {
                "edit_linear_issue": edit_linear_issue,
            }
            new_messages.append(response_message)
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
                new_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
            second_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=new_messages,
            )  # get a new response from the model where it can see the function response
            return second_response
    
    create_linear_issue(title, description, linear_client)
    

def _handle_other(_description: str):
    pass

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
                            "description": "Title of the bug report or feature request described in the conversation",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the bug report or feature request described in the conversation",
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
        messages.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                title=function_args.get("title"),
                description=function_args.get("description"),
                openai_client=openai_client,
                messages=messages,
            )
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response
        second_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )  # get a new response from the model where it can see the function response
        return second_response

def test_cases():
    bug_report_1 = "[User]: 'I can't change my delivery address', [Agent]: 'Sorry for the inconvenience we will get that fixed right away'"

    feature_request_1 = "[User]: 'I would like to be able to change my delivery address', [Agent]: 'Thanks for the suggestion!'"

    general_query_1 = "[User]: 'Hi, I can't figure out how to change my delivery address', [Agent]: 'You can change it by going to Settings > User Information > Address', [User]: 'Thanks!'"

    categorize_conversation(bug_report_1)


if __name__ == "__main__":
    test_cases()