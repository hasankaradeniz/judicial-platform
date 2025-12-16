from core.models import JudicialDecision

print('JudicialDecision model alanları:')
for field in JudicialDecision._meta.fields:
    print(f'- {field.name}: {field.__class__.__name__}')
