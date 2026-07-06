# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
import os
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "planetarian")
SECRET_KEY     = os.environ.get("SECRET_KEY", "gentle-jena-cv")
# 你的網站 repo 路徑（含 index.html 那層）
SITE_REPO      = os.environ.get("SITE_REPO", os.path.join(os.path.dirname(__file__), "..", "..", "robinsixrainbow.github.io"))
PORT           = int(os.environ.get("PORT", "8100"))
