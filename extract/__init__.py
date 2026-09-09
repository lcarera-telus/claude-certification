"""extract — turn an unstructured invoice into schema-validated JSON.

Modules:

  client.py     Builds the Anthropic client and resolves the default model.
                Reads credentials from the environment, never from source.
  validate.py   Loads the JSON Schema and reports errors as data. Imports no
                API package, so the whole validation layer runs offline.
  extractor.py  Forces a tool call, reads the structured result, validates it,
                and retries exactly once with the concrete failures fed back.

Read extractor.py first. Its opening comment block explains why this pipeline
forces a tool call instead of asking the model for "JSON only".
"""
