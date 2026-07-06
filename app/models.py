"""cv_backend models — mirror the live site's CV_DATA + I18N content shapes.
Trilingual content = one row per logical item with _en/_zh/_ja columns."""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Journal(Base):
    __tablename__ = "journals"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    q: Mapped[str] = mapped_column(default="")            # Q1/Q2…
    authors: Mapped[str] = mapped_column(default="")      # HTML（含 <span class="me">）
    title: Mapped[str] = mapped_column(default="")
    journal: Mapped[str] = mapped_column(default="")
    vol: Mapped[str] = mapped_column(default="")
    doi: Mapped[str] = mapped_column(default="")


class Conference(Base):
    __tablename__ = "conferences"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    venue: Mapped[str] = mapped_column(default="")
    meta_text: Mapped[str] = mapped_column("meta", default="")  # wtforms 保留名迴避
    title: Mapped[str] = mapped_column(default="")
    invited: Mapped[bool] = mapped_column(default=False)


class Competition(Base):
    __tablename__ = "competitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    year: Mapped[str] = mapped_column(default="")
    award: Mapped[str] = mapped_column(default="")
    body: Mapped[str] = mapped_column(default="")


class Patent(Base):
    __tablename__ = "patents"
    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(default="tw")     # tw / cn / us
    sort: Mapped[int] = mapped_column(default=0)
    pid: Mapped[str] = mapped_column(default="")          # 證書號
    date: Mapped[str] = mapped_column(default="")
    title: Mapped[str] = mapped_column(default="")


class Education(Base):
    __tablename__ = "education"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    school_en: Mapped[str] = mapped_column(default="")
    school_zh: Mapped[str] = mapped_column(default="")
    school_ja: Mapped[str] = mapped_column(default="")
    degree_en: Mapped[str] = mapped_column(default="")
    degree_zh: Mapped[str] = mapped_column(default="")
    degree_ja: Mapped[str] = mapped_column(default="")
    date_en: Mapped[str] = mapped_column(default="")
    date_zh: Mapped[str] = mapped_column(default="")
    date_ja: Mapped[str] = mapped_column(default="")
    place_en: Mapped[str] = mapped_column(default="")
    place_zh: Mapped[str] = mapped_column(default="")
    place_ja: Mapped[str] = mapped_column(default="")


class SkillGroup(Base):
    __tablename__ = "skill_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    ttl_en: Mapped[str] = mapped_column(default="")
    ttl_zh: Mapped[str] = mapped_column(default="")
    ttl_ja: Mapped[str] = mapped_column(default="")
    items_en: Mapped[str] = mapped_column(default="")     # 每行一項
    items_zh: Mapped[str] = mapped_column(default="")
    items_ja: Mapped[str] = mapped_column(default="")


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    label_en: Mapped[str] = mapped_column(default="")
    label_zh: Mapped[str] = mapped_column(default="")
    label_ja: Mapped[str] = mapped_column(default="")
    org_en: Mapped[str] = mapped_column(default="")
    org_zh: Mapped[str] = mapped_column(default="")
    org_ja: Mapped[str] = mapped_column(default="")


class Experience(Base):
    __tablename__ = "experience"
    id: Mapped[int] = mapped_column(primary_key=True)
    sort: Mapped[int] = mapped_column(default=0)
    role_en: Mapped[str] = mapped_column(default="")
    role_zh: Mapped[str] = mapped_column(default="")
    role_ja: Mapped[str] = mapped_column(default="")
    date_en: Mapped[str] = mapped_column(default="")
    date_zh: Mapped[str] = mapped_column(default="")
    date_ja: Mapped[str] = mapped_column(default="")
    org_en: Mapped[str] = mapped_column(default="")
    org_zh: Mapped[str] = mapped_column(default="")
    org_ja: Mapped[str] = mapped_column(default="")
    project_en: Mapped[str] = mapped_column(default="")
    project_zh: Mapped[str] = mapped_column(default="")
    project_ja: Mapped[str] = mapped_column(default="")
    star_s_en: Mapped[str] = mapped_column(default="")
    star_s_zh: Mapped[str] = mapped_column(default="")
    star_s_ja: Mapped[str] = mapped_column(default="")
    star_t_en: Mapped[str] = mapped_column(default="")
    star_t_zh: Mapped[str] = mapped_column(default="")
    star_t_ja: Mapped[str] = mapped_column(default="")
    star_a_en: Mapped[str] = mapped_column(default="")
    star_a_zh: Mapped[str] = mapped_column(default="")
    star_a_ja: Mapped[str] = mapped_column(default="")
    star_r_en: Mapped[str] = mapped_column(default="")
    star_r_zh: Mapped[str] = mapped_column(default="")
    star_r_ja: Mapped[str] = mapped_column(default="")
