import os
import re


def update_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Models mapping
    content = re.sub(
        r"from app\.models\.(device|rack) import",
        r"from app.domains.hardware.models import",
        content,
    )
    content = re.sub(
        r"from app\.models\.(cable|interface) import",
        r"from app.domains.cabling.models import",
        content,
    )
    content = re.sub(
        r"from app\.models\.usv import",
        r"from app.domains.power.models import",
        content,
    )
    # Remove dead models from imports if they exist
    content = re.sub(r",\s*DistributionPanel", "", content)
    content = re.sub(r",\s*DistributionCircuit", "", content)
    content = re.sub(r",\s*KentixReading", "", content)
    content = re.sub(r",\s*UsvCalculation", "", content)
    content = re.sub(r"DistributionPanel,\s*", "", content)
    content = re.sub(r"DistributionCircuit,\s*", "", content)
    content = re.sub(r"KentixReading,\s*", "", content)
    content = re.sub(r"UsvCalculation,\s*", "", content)

    # Replace DevicePort and ServerInterface with Interface
    content = re.sub(r"DevicePort", "Interface", content)
    content = re.sub(r"ServerInterface", "Interface", content)

    # Schemas mapping (this is tricky because serverflow had everything)
    hardware_schemas = [
        "Rack",
        "RackCreate",
        "RackUpdate",
        "Device",
        "DeviceCreate",
        "DeviceUpdate",
        "PduOutlet",
        "PduOutletCreate",
        "PduOutletUpdate",
    ]
    cabling_schemas = [
        "Cable",
        "CableCreate",
        "CableUpdate",
        "CableStrand",
        "CableStrandCreate",
        "CableStrandUpdate",
        "Interface",
        "InterfaceCreate",
        "InterfaceUpdate",
        "InterfaceBody",
    ]
    power_schemas = [
        "UsvUnit",
        "UsvUnitCreate",
        "UsvUnitUpdate",
        "UsvModule",
        "UsvModuleCreate",
        "UsvModuleUpdate",
    ]

    # We just replace `from app.schemas.serverflow import X, Y, Z` with individual imports
    def schema_replacer(match):
        imports_str = match.group(1)
        imports = [i.strip() for i in imports_str.split(",")]

        hw = []
        cab = []
        pow_s = []

        for imp in imports:
            if imp in hardware_schemas:
                hw.append(imp)
            elif imp in cabling_schemas:
                cab.append(imp)
            elif imp in power_schemas:
                pow_s.append(imp)

        res = []
        if hw:
            res.append(f"from app.domains.hardware.schemas import {', '.join(hw)}")
        if cab:
            res.append(f"from app.domains.cabling.schemas import {', '.join(cab)}")
        if pow_s:
            res.append(f"from app.domains.power.schemas import {', '.join(pow_s)}")

        return "\n".join(res)

    content = re.sub(
        r"from app\.schemas\.serverflow import \((.*?)\)",
        lambda m: schema_replacer(m).replace("\n", " "),
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"from app\.schemas\.serverflow import (.*)", schema_replacer, content
    )

    with open(filepath, "w") as f:
        f.write(content)


# Refactor all routers and services
for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py") and ("endpoints" in root or "services" in root):
            update_file(os.path.join(root, file))
