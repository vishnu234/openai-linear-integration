from openai import OpenAI
import json
from constants import OPENAI_KEY


def delivery_test():
    def get_optimal_delivery(start_location, end_location):
        if start_location == "San Francisco, USA" and end_location == "Beijing, China":
            return "air"
        elif start_location == "San Francisco, USA" and end_location == "Berkeley, USA":
            return "ground"

    openai_client = OpenAI(
        api_key=OPENAI_KEY,
    )
    messages = [
        {
            "role": "user",
            "content": "I have a package I want to deliver from San Francisco. If I want to deliver it to Hyderabad, should I ship it by air or ground?",
        }
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_optimal_delivery",
                "description": "Get the optimal delivery route for a particular start and end",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_location": {
                            "type": "string",
                            "description": "City and country, e.g. San Francisco, USA",
                        },
                        "end_location": {
                            "type": "string",
                            "description": "City and country, e.g. San Francisco, USA",
                        },
                    },
                    "required": ["start_location", "end_location"],
                },
            },
        }
    ]
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    import pdb

    pdb.set_trace()


def online_example():
    def get_current_weather(location, unit="fahrenheit"):
        """Get the current weather in a given location"""
        if "tokyo" in location.lower():
            return json.dumps({"location": "Tokyo", "temperature": "10", "unit": unit})
        elif "san francisco" in location.lower():
            return json.dumps(
                {"location": "San Francisco", "temperature": "72", "unit": unit}
            )
        elif "paris" in location.lower():
            return json.dumps({"location": "Paris", "temperature": "22", "unit": unit})
        else:
            return json.dumps({"location": location, "temperature": "unknown"})

    openai_client = OpenAI(
        api_key=OPENAI_KEY,
    )
    messages = [
        {
            "role": "user",
            "content": "What's the weather like in San Francisco, Tokyo, and Paris?",
        }
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    # import pdb ; pdb.set_trace()
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
    )
    # import pdb ; pdb.set_trace()
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    # Step 2: check if the model wanted to call a function
    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_current_weather": get_current_weather,
        }  # only one function in this example, but you can have multiple
        messages.append(response_message)  # extend conversation with assistant's reply
        # Step 4: send the info for each function call and function response to the model
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                location=function_args.get("location"),
                unit=function_args.get("unit"),
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


if __name__ == "__main__":
    print(online_example())
