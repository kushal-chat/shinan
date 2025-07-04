from llama_index.readers.web import SimpleWebPageReader

# In the future, we can use the HatenaBlogReader to read the blog posts. THis
reader = SimpleWebPageReader()
documents = reader.load_data(["https://www.softbank.jp/sbnews/entry/20250626_02"])

print(documents)