from ingestion.retrieval.retriever import semantic_search, format_context_for_llm

query = "DPF soot load too high"

print(f"\n Query: {query}\n")

results = semantic_search(query, top_k=3)

if not results:
    print(" No results found")
else:
    for i, r in enumerate(results, 1):
        print(f"Result {i}")
        print(f"DTC Code : {r['dtc_code']}")
        print(f"Category : {r['category']}")
        print(f"Score    : {round(r['score'], 3)}")
        print(f"Text     : {r['chunk_text'][:150]}...")
        print("-" * 50)

# Optional: format for LLM
context = format_context_for_llm(results)

print("\n Formatted Context for LLM:\n")
print(context)

