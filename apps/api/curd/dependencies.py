class ModelGetter:
    def __init__(self, query_model):
        self.query_model = query_model

    def __call__(self):
        return self.query_model
