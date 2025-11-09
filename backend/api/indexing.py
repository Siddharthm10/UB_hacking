from textwrap import wrap


def chunk_transcript(messages, chunk_size=1200):
    buffer = []
    current = ''
    for message in messages:
        entry = f"{message.get('role','agent')}: {message.get('text','')}\n"
        if len(current) + len(entry) > chunk_size and current:
            buffer.append(current.strip())
            current = entry
        else:
            current += entry
    if current:
        buffer.append(current.strip())
    return buffer


def build_embeddings(chunks):
    # Stub to show where embeddings would be created
    return [{'chunk': chunk, 'vector': wrap(chunk[:120], 20)} for chunk in chunks]
