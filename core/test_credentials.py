# Test credential update
import re

with open("/var/www/judicial_platform/core/param_simple_service.py", "r") as f:
    content = f.read()

# Find and replace the credentials section
lines = content.split("\n")
new_lines = []
in_init = False
added_test = False

for i, line in enumerate(lines):
    if "def __init__(self):" in line:
        in_init = True
        new_lines.append(line)
    elif in_init and "self.client_code = " in line and not added_test:
        # Add test/production logic
        new_lines.append("        # Test/Production mode - Set to False for production")
        new_lines.append("        self.test_mode = getattr(settings, \"PARAM_TEST_MODE\", False)")
        new_lines.append("        ")
        new_lines.append("        if self.test_mode:")
        new_lines.append("            # Test credentials")
        new_lines.append("            self.client_code = \"10738\"")
        new_lines.append("            self.username = \"Test\"")
        new_lines.append("            self.password = \"Test\"")
        new_lines.append("            self.guid = \"0c13d406-873b-403b-9c09-a5766840d98c\"")
        new_lines.append("        else:")
        new_lines.append("            # Production credentials")
        new_lines.append("            self.client_code = getattr(settings, \"PARAM_CLIENT_CODE\", \"145942\")")
        new_lines.append("            self.username = getattr(settings, \"PARAM_CLIENT_USERNAME\", \"TP10173244\")")
        new_lines.append("            self.password = getattr(settings, \"PARAM_CLIENT_PASSWORD\", \"E78A466F0083A439\")")
        new_lines.append("            self.guid = getattr(settings, \"PARAM_GUID\", \"E204D733-02BA-4312-B03F-84BFE184313C\")")
        added_test = True
        # Skip the next 4 lines (old credentials)
        for j in range(4):
            if i + j + 1 < len(lines):
                lines[i + j + 1] = None
    elif line is not None:
        if not (in_init and line is None):
            new_lines.append(line)

# Remove the old test_mode line if it exists later
final_lines = []
for line in new_lines:
    if line and "self.test_mode = getattr(settings" in line and added_test:
        continue
    final_lines.append(line)

with open("/var/www/judicial_platform/core/param_simple_service.py", "w") as f:
    f.write("\n".join(final_lines))

print("Test credentials added successfully")
