from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Get collection info
collection_name = "chatbot_knowledge"
info = client.get_collection(collection_name)

print(f"Collection: {collection_name}")
print(f"Total vectors: {info.points_count}")
print(f"Vector size: {info.config.params.vectors.size}")
print(f"Distance: {info.config.params.vectors.distance}")

# Get some sample points
points = client.scroll(
    collection_name=collection_name,
    limit=5,
    with_payload=True,
    with_vectors=False
)

print(f"\nFirst {len(points[0])} documents:")
for i, point in enumerate(points[0], 1):
    print(f"\n--- Document {i} ---")
    print(f"ID: {point.id}")
    print(f"Content: {point.payload.get('content', '')[:100]}...")
    print(f"Metadata: {point.payload.get('metadata', {})}")