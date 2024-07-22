LINEAR_TEAM_ID = "a409ee5a-1f47-4e5f-bf16-332272fefacf"

# Reading from text files from now to avoid pushing these keys...
with open("openai_key.txt") as f:
    OPENAI_KEY = f.read().strip("\n")

with open("linear_key.txt") as f:
    LINEAR_KEY = f.read().strip("\n")