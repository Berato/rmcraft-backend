from typing import Any, Dict, List


def ensure_list_of_dicts(x: Any) -> list:
    """Coerce input into a list of dicts where possible."""
    if x is None:
        return []
    if isinstance(x, dict):
        # maybe stored as single object
        return [x]
    if isinstance(x, list):
        out = []
        for item in x:
            if isinstance(item, dict):
                out.append(item)
            else:
                # strings or primitives -> try to wrap
                out.append({"name": item})
        return out
    # primitive (str/int) -> wrap
    return [{"name": x}]


def normalize_skills(skills: Any) -> list:
    """Normalize skills to a list of skill-like dicts: {id?, name, level?}."""
    if skills is None:
        return []
    if isinstance(skills, dict):
        # dict-of-categories: flatten values
        out = []
        for cat, vals in skills.items():
            if isinstance(vals, list):
                for v in vals:
                    if isinstance(v, dict):
                        out.append(v)
                    else:
                        out.append({"name": v})
            else:
                out.append({"name": vals})
        return out
    if isinstance(skills, list):
        out = []
        for s in skills:
            if isinstance(s, dict):
                out.append(s)
            else:
                out.append({"name": s})
        return out
    # fallback
    return [{"name": skills}]


def normalize_projects(projects: Any) -> list:
    if projects is None:
        return []
    if isinstance(projects, dict):
        return [projects]
    if isinstance(projects, list):
        out = []
        for p in projects:
            if isinstance(p, dict):
                # some rows use 'title' instead of 'name'
                if "name" not in p and "title" in p:
                    p["name"] = p.get("title")
                out.append(p)
            else:
                out.append({"name": p})
        return out
    return [{"name": projects}]


def normalize_personal_info(pi: Any) -> dict:
    if not pi:
        return {}
    if isinstance(pi, dict):
        # ensure id exists as a string to satisfy strict models
        if "id" not in pi or pi.get("id") is None:
            pi["id"] = ""
        return pi
    # primitive
    return {"id": "", "firstName": str(pi)}
