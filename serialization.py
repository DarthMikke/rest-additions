class SerializableMixin:
    fields: list = []
    meta_fields: list = []

    def serialize(self):
        serialized = {}
        for field in self.SerializerMeta.fields:
            if isinstance(field, str):
                value = self.__getattribute__(field)
            else:
                (field, serializer) = field
                value = serializer(self.__getattribute__(field))

            if callable(value):
                print(value)
                value = value()

            serialized[field] = value
        
        try:
            meta = self.serializer_meta_fields
        except Exception as e:
            meta = []
        for field in meta:
            serialized[field[0]] = field[1](self)

        return serialized
