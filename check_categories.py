from core.models import JudicialDecision
from django.db.models import Count

total = JudicialDecision.objects.count()
categorized = JudicialDecision.objects.exclude(detected_legal_area__isnull=True).exclude(detected_legal_area='').count()

print(f'Toplam karar: {total}')
print(f'Kategorize edilmiş: {categorized}')
print(f'Yüzde: {(categorized/total*100):.2f}%' if total > 0 else '0%')

areas = JudicialDecision.objects.exclude(detected_legal_area__isnull=True).exclude(detected_legal_area='').values('detected_legal_area').annotate(count=Count('id')).order_by('-count')

print('\nHukuk alanlarına göre dağılım:')
for area in areas[:10]:
    print(f"{area['detected_legal_area']}: {area['count']} karar")
