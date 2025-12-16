import re

# Read the current admin.py
with open("admin.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add format_html import if not present
if "from django.utils.html import format_html" not in content:
    content = content.replace(
        "from django.contrib import admin",
        "from django.contrib import admin\nfrom django.utils.html import format_html"
    )

# Add helper function
helper_function = """
# Hierarchy helper function
def get_hierarchy_display(category):
    level = 0
    current = category
    while current and current.ust_kategori:
        level += 1
        current = current.ust_kategori
    return "　" * level + ("└─ " if level > 0 else "") + category.ad

"""

# Add helper function after imports
content = content.replace("# Mevcut modeller", helper_function + "# Mevcut modeller")

# Update MevzuatKategoriAdmin
old_kategori_admin = """@admin.register(MevzuatKategori)
class MevzuatKategoriAdmin(admin.ModelAdmin):
    list_display = [ad, kod, ust_kategori, aktif]
    list_filter = [aktif, ust_kategori]
    search_fields = [ad, kod]
    ordering = [ad]"""

new_kategori_admin = """@admin.register(MevzuatKategori)
class MevzuatKategoriAdmin(admin.ModelAdmin):
    list_display = [hierarchy_name, kod, alt_kategori_sayisi, aktif]
    list_filter = [aktif, ust_kategori]
    search_fields = [ad, kod, aciklama]
    ordering = [ust_kategori__ad, ad]
    
    def hierarchy_name(self, obj):
        return get_hierarchy_display(obj)
    hierarchy_name.short_description = "Kategori (Hiyerarşik)"
    
    def alt_kategori_sayisi(self, obj):
        count = obj.mevzuatkategori_set.count()
        return f"{count} alt" if count > 0 else "-"
    alt_kategori_sayisi.short_description = "Alt Kategoriler" """

content = content.replace(old_kategori_admin, new_kategori_admin)

# Write the updated file
with open("admin.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated admin.py with hierarchical categories\!")
