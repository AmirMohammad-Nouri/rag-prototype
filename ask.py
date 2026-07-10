from rag_pipeline import answer_question

def main():
    print("RAG prototype — ask a question (type 'exit' to quit)\n")
    while True:
        question = input("> ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        result = answer_question(question)

        print(f"\n{result['answer']}\n")
        if result["sources"]:
            print("Sources:")
            for s in result["sources"]:
                print(f"  - {s['source_filename']} (page/section {s['location']}, dept: {s['department']})")
        if result["usage"]:
            print(f"\n[tokens: {result['usage']['total_tokens']}]")
        print()

if __name__ == "__main__":
    main()
    