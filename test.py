import openai
import json  # Import JSON for proper serialization

# Set the API key and base URL for Exaone
openai.api_key = "flp_EUGAW1hNHAFgtE4dIgivHZZTCOg4iQiKrFRzwqdL0Uhd3"  # Replace with your actual API key
openai.api_base = "https://api.friendli.ai/serverless/v1"

# Define the data as a Python object (list of dictionaries)
data = [
    {
        "source": "jira",
        "type": "issue_activity",
        "issue_key": "CLUSTWORK-15875",
        "summary": "dolphine5 Demo Application",
        "status": "Open",
        "assignee": "나상엽 sangyeob.na",
        "reporter": "나상엽 sangyeob.na",
        "created": "2025-08-28T13:01:32.000+0900",
        "updated": "2025-09-16T10:27:30.000+0900",
        "url": "http://jira.lge.com/issue/browse/CLUSTWORK-15875",
    },
    {
        "source": "jira",
        "type": "issue_activity",
        "issue_key": "MQBFPK-29306",
        "summary": "[FPK] Need to check FAS Animation with Idle state",
        "status": "Open",
        "assignee": "THANG DINH VU thang3.vu",
        "reporter": "나상엽 sangyeob.na",
        "created": "2025-09-15T14:38:26.000+0900",
        "updated": "2025-09-17T18:37:52.000+0900",
        "url": "http://jira.lge.com/issue/browse/MQBFPK-29306",
    },
    # Add more items here...
]

# Serialize the data to a JSON string
data_json = json.dumps(data, ensure_ascii=False, indent=4)

# Create a chat completion request
response = openai.ChatCompletion.create(
    model="LGAI-EXAONE/EXAONE-4.0.1-32B",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Summarize the work and issue to shorter paragraph "},
        {"role": "user", "content": data_json},
    ],
)

# Print the response from Exaone
print(response["choices"][0]["message"]["content"])
