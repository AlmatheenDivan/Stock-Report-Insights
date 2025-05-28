
try:
    from langchain_community.llms import OpenAI
    import os
    if os.getenv("AZURE_OPENAI_API_KEY"):
        llm = OpenAI(
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            model_name="gpt-4",
            deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
    else:
        llm = None  

except ImportError:
    llm = None

except Exception as e:

    print(f"[INFO] LangChain LLM placeholder failed to load: {e}")
    llm = None
