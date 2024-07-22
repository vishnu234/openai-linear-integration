from openai import OpenAI
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
import json

from linear_helpers import list_issues, create_issue, edit_issue
from constants import LINEAR_KEY, LINEAR_TEAM_ID, OPENAI_KEY

# TODO: Should we pull out GPT API calls into a separate gpt_helpers.py file?
# TODO: Should we have one team for FRs and one team for BRs?


# Is it advantageous to have one prompt per linear task? Or one prompt for all linear tasks?
# An evaluation suite will help answer this question.
def categorize_conversation(conversation: str) -> None:
    """ """
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": LINEAR_KEY},
    )
    linear_client = Client(transport=transport, fetch_schema_from_transport=True)
    openai_client = OpenAI(
        api_key=OPENAI_KEY,
    )

    # First, we iterate over every task to see if this conversation matches any existing tasks
    issues = list_issues(client=linear_client, team_id=LINEAR_TEAM_ID)["team"][
        "issues"
    ]["nodes"]
    for issue in issues:
        # Perhaps instead of this binary yes/no decision and iterating over each issue,
        # we can get something analogous to a confidence score from the model and maximize
        # that across all existing issues? Or we could prompt the model to tell us which
        # issue the conversation most closely resembles, if any?
        prompt = f"""Does the following conversation describe a new bug report and/or feature request that isn't described in the following existing task?
        Conversation: {conversation}. Existing Task Title: {issue["title"]}. Existing Task Description: {issue["description"]}. 
        If this issue is already described in the existing task, can you update that task's title and description, especially noting the number of times the issue described in the task has been mentioned by users?
        If the issue described in the conversation is different from the issue described in the existing task, please do not update the existing task!
        If the conversation captures neither a feature request nor a bug report (e.g. if the Agent was able to successfully answer the User's question), please don't update an existing task!
        """
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
                    "name": "edit_issue",
                    "description": "Updates the title and description of a task in Linear using the Linear GraphQL API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "new_title": {
                                "type": "string",
                                "description": "The updated title of the existing task resulting from the bug report and/or feature request described in the conversation",
                            },
                            "new_description": {
                                "type": "string",
                                "description": "The updated description of the existing task resulting from the bug report and/or feature request described in the conversation",
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
        if tool_calls:
            available_functions = {
                "edit_issue": edit_issue,
            }
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(
                    client=linear_client,
                    issue_id=issue["id"],
                    new_title=function_args.get("new_title"),
                    new_description=function_args.get("new_description"),
                )
                issue_dict = function_response["issueUpdate"]["issue"]
                print(
                    f"Added information from this conversation to an existing linear task! \nID: {issue_dict['id']} \nTitle: {issue_dict['title']} \nDescription: {issue_dict['description']}"
                )
                return

    # Since this conversation didn't match any of the existing tasks, or isn't describing a
    # bug report or feature request, we either make a new task if this does describe a bug
    # report or feature request, or discard this altogether
    new_task_prompt = f"""
    If there is a feature request or bug report described in the following conversation, please create a new task for it. 
    Otherwise, for example if the Agent was successfully able to answer a user's question, please do not create a new task!
    Conversation: {conversation}
    """
    new_task_messages = [
        {
            "role": "user",
            "content": new_task_prompt,
        }
    ]
    new_issue_function_tools = [
        {
            "type": "function",
            "function": {
                "name": "create_issue",
                "description": "Creates a new task in linear using the GraphQL API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title for the task. This title summarizes the feature request/bug report described in the conversation",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for the task. This description is a more length summary of the feature request/bug report described in the conversation",
                        },
                    },
                },
            },
        },
    ]
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=new_task_messages,
        tools=new_issue_function_tools,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    if tool_calls:
        available_functions = {
            "create_issue": create_issue,
        }
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                client=linear_client,
                title=function_args.get("title"),
                description=function_args.get("description"),
                team_id=LINEAR_TEAM_ID,
            )
            issue_dict = function_response["issueCreate"]["issue"]
            print(
                f"Created new linear task for this conversation! \nID: {issue_dict['id']} \nTitle: {issue_dict['title']} \nDescription: {issue_dict['description']}"
            )
    else:
        print(
            "Did not create a new task for the input conversation because it didn't describe a bug report or feature request!"
        )


def test_cases() -> None:
    bug_report_1 = "[User]: 'I can't change my delivery address', [Agent]: 'Sorry for the inconvenience we will get that fixed right away'"

    feature_request_1 = "[User]: 'I would like to be able to change my delivery address', [Agent]: 'Thanks for the suggestion!'"

    general_query_1 = "[User]: 'Hi, I can't figure out how to change my delivery address', [Agent]: 'You can change it by going to Settings > User Information > Address', [User]: 'Thanks!'"

    bug_report_2 = "[User]: 'I can't change my profile picture', [Agent]: 'Sorry for the inconvenience we will get that fixed right away'"

    feature_request_2 = "[User]: 'I would like to be able to change my profile picture', [Agent]: 'Thanks for the suggestion!'"

    general_query_2 = "[User]: 'Hi, I can't figure out how to change my profile picture', [Agent]: 'You can change it by going to Settings > User Information > Profile Picture', [User]: 'Thanks!'"

    bug_report_3 = "[User]: 'My location won't change even after I enter my new location', [Agent]: 'Sorry for the inconvenience we will get that fixed right away'"

    feature_request_3 = "[User]: 'I would like to be able to change my current location', [Agent]: 'Thanks for the suggestion!'"

    general_query_3 = "[User]: 'Hi, I can't figure out how to change my current locatino', [Agent]: 'You can change it by going to Settings > User Information > Current Location', [User]: 'Thanks!'"

    categorize_conversation(bug_report_3)


if __name__ == "__main__":
    test_cases()
