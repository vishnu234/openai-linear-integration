# openai-linear-integration
Integration with the OpenAI function calling API and Linear GraphQL API

## Repo Structure

`main.py`: Contains the core code, including the `categorize_conversation()` function which takes in the conversation as a string, categorizes it using the OpenAI Function Calling API, and ingests it into a Linear project using the Linear GraphQL API. 

`examples/`: Some example scripts I wrote to get more familiar with the OpenAI and Linear APIs. Feel free to ignore

`constants.py`: Defines some important constants shared between files

`linear_helpers.py`: Defines some helper functions to communicate with the Linear GraphQL API 

## State of Current Work
The existing function could definitely be improved and tested on a larger suite of prompts used for evaluation. However, I thought it would be best to share what I have currently as it shows the basic structure of how this could be done, with the understanding that certain things like prompt structure and prompting strategies could be refined with more real world data and experimentation.

## Running the Code

`pip install -r requirements.txt` to install dependencies

`python main.py`

I created a fresh Python 3.10 Anaconda environment for this project