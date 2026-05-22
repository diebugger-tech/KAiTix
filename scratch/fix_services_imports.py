import os
import re


def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Update service imports
    content = re.sub(
        r"from app\.services\.usv_calc",
        "from app.domains.power.services.usv_calc",
        content,
    )
    content = re.sub(
        r"from app\.services\.eplan_parser",
        "from app.domains.import_export.services.eplan_parser",
        content,
    )
    content = re.sub(
        r"from app\.services\.export_service",
        "from app.domains.import_export.services.export_service",
        content,
    )
    content = re.sub(
        r"from app\.services\.rack_pdf",
        "from app.domains.import_export.services.rack_pdf",
        content,
    )
    content = re.sub(
        r"from app\.services\.topology_pdf",
        "from app.domains.import_export.services.topology_pdf",
        content,
    )

    # Update endpoints imports that were missed (if any)
    content = re.sub(
        r"from app\.api\.endpoints\.usv", "from app.domains.power.routers.usv", content
    )

    with open(filepath, "w") as f:
        f.write(content)


for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py"):
            update_file(os.path.join(root, file))
