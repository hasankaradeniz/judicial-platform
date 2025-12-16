# Fix search_results.html template
with open("core/templates/core/search_results.html", "r") as f:
    content = f.read()

# Replace the problematic line 
old_line = "{% if query %}{% for decision in decisions %}{% else %}{% for decision in newest_decisions %}{% endif %}"
new_structure = """{% if query %}
        {% for decision in decisions %}"""

content = content.replace(old_line, new_structure)

# Find and fix the endfor structure
content = content.replace("{% endfor %}", """{% endfor %}
      {% else %}
        {% for decision in newest_decisions %}
        <\!-- Decision content same as above -->
        {% endfor %}
      {% endif %}""", 1)

with open("core/templates/core/search_results.html", "w") as f:
    f.write(content)

print("Template fixed")
