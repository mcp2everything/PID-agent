from langchain_deepseek import ChatDeepSeek
from config.settings import settings

def main():
    """
    Demo program to test DeepSeek API call.
    """
    llm = ChatDeepSeek(
        temperature=0.3,
        max_tokens=512,
        model='deepseek-chat',
        api_key=settings.DEEPSEEK_API_KEY,
    )

    try:
        response = llm.invoke("你好，DeepSeek!")
        print("DeepSeek API call successful!")
        print("Response:")
        print(response)
    except Exception as e:
        print("DeepSeek API call failed!")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
