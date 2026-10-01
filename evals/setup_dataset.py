import os
import json
from langsmith import Client

def setup():
    client = Client()
    ds_name = "school_chatbot_evals"
    
    if client.has_dataset(dataset_name=ds_name):
        client.delete_dataset(dataset_name=ds_name)
        
    dataset = client.create_dataset(
        dataset_name=ds_name,
        description="Dataset for chatbot evaluation across various slices"
    )
    
    inputs = []
    outputs = []
    metadata = []
    
    with open("evals/dataset.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            record = json.loads(line)
            inputs.append(record["inputs"])
            outputs.append(record["reference_outputs"])
            metadata.append({"slice": record["slice"]})
            
    client.create_examples(
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        dataset_id=dataset.id
    )
    print(f"Created {len(inputs)} examples in dataset {ds_name}")

if __name__ == "__main__":
    setup()
