# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
"""cv_backend admin — sqladmin 後台（中文標籤）＋登入退避。"""
import time
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from . import models as M
from .settings import ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY


class Auth(AuthenticationBackend):
    _fails = {}

    def _ip(self, request):
        return request.client.host if request.client else "?"

    async def login(self, request: Request) -> bool:
        ip = self._ip(request)
        n, t = self._fails.get(ip, (0, 0.0))
        wait = min(2 ** max(0, n - 2), 60)
        if n >= 3 and time.time() - t < wait:
            return False
        form = await request.form()
        ok = (form.get("username") == ADMIN_USERNAME and form.get("password") == ADMIN_PASSWORD)
        if ok:
            self._fails.pop(ip, None)
            request.session.update({"token": "ok"})
        else:
            self._fails[ip] = (n + 1, time.time())
        return ok

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("token") == "ok"


class JournalAdmin(ModelView, model=M.Journal):
    name = "期刊論文"; name_plural = "期刊論文"; icon = "fa-solid fa-book"
    column_list = [M.Journal.sort, M.Journal.q, M.Journal.title, M.Journal.journal]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class ConferenceAdmin(ModelView, model=M.Conference):
    name = "研討會"; name_plural = "研討會"; icon = "fa-solid fa-microphone"
    column_list = [M.Conference.sort, M.Conference.venue, M.Conference.title, M.Conference.invited]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class CompetitionAdmin(ModelView, model=M.Competition):
    name = "競賽獲獎"; name_plural = "競賽獲獎"; icon = "fa-solid fa-trophy"
    column_list = [M.Competition.sort, M.Competition.year, M.Competition.award, M.Competition.body]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class PatentAdmin(ModelView, model=M.Patent):
    name = "發明專利"; name_plural = "發明專利"; icon = "fa-solid fa-certificate"
    column_list = [M.Patent.sort, M.Patent.region, M.Patent.pid, M.Patent.title]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class EducationAdmin(ModelView, model=M.Education):
    name = "學歷"; name_plural = "學歷"; icon = "fa-solid fa-graduation-cap"
    column_list = [M.Education.sort, M.Education.school_zh, M.Education.degree_zh]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class SkillGroupAdmin(ModelView, model=M.SkillGroup):
    name = "技能群組"; name_plural = "技能群組"; icon = "fa-solid fa-screwdriver-wrench"
    column_list = [M.SkillGroup.sort, M.SkillGroup.ttl_zh]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class RoleAdmin(ModelView, model=M.Role):
    name = "現任職務"; name_plural = "現任職務"; icon = "fa-solid fa-id-badge"
    column_list = [M.Role.sort, M.Role.label_zh, M.Role.org_zh]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


class ExperienceAdmin(ModelView, model=M.Experience):
    name = "工作經歷"; name_plural = "工作經歷"; icon = "fa-solid fa-briefcase"
    column_list = [M.Experience.sort, M.Experience.role_zh, M.Experience.org_zh]
    form_excluded_columns = ["id"]; column_default_sort = [("sort", False), ("id", False)]; page_size = 50


def mount_admin(app, engine):
    admin = Admin(app, engine, title="CV 管理 — planetarium 後台",
                  authentication_backend=Auth(secret_key=SECRET_KEY))
    for v in (JournalAdmin, ConferenceAdmin, CompetitionAdmin, PatentAdmin,
              EducationAdmin, SkillGroupAdmin, RoleAdmin, ExperienceAdmin):
        admin.add_view(v)
    return admin
