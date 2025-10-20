# core/nlp_utils.py
import stanza

# Pipeline'ı uygulamanın başında oluşturmak, her istek için yeniden başlatılmasını engeller.
# Bu kodu, modül yüklendiğinde bir kez çalıştırılacak şekilde ayarlıyoruz.
nlp = stanza.Pipeline('tr', processors='tokenize,ner', verbose=False)

def analyze_text(text):
    """
    Girilen Türkçe metni analiz eder ve tespit edilen varlıkları (NER) liste olarak döndürür.
    Hukuki metinlerde taraf isimleri, olay yerleri, tarih gibi bilgileri yakalayabilir.
    """
    doc = nlp(text)
    entities = []
    for sentence in doc.sentences:
        for ent in sentence.ents:
            entities.append(ent.text)
    return entities
