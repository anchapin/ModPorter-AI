with open("backend/requirements.txt", "r") as f:
    text = f.read()

text = text.replace("pydantic[email]~=2.11.9", "pydantic~=2.11.9")
text = text.replace("python-dotenv~=1.1.1\n", "python-dotenv~=1.1.1\nbcrypt>=4.2.0\n")

with open("backend/requirements.txt", "w") as f:
    f.write(text)
