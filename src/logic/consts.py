# BATCH_SIZE: controls how many embeddings can be written to the DB at once
BATCH_SIZE = 100000

# EMBEDDING_LENGTH: controls the length of the embedding vectors provided by run_model
# NOTE:
# value is kept low for demo purposes as large values
# significantly increase database write times and balloon database size
EMBEDDING_LENGTH = 10

# GENE_POOL_SIZE: controls how many genes are available in the database
GENE_POOL_SIZE = 1000
