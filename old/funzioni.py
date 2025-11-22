"""funzioni per main.py"""

import streamlit as st


def read_enrollments_from_state(enrollment_key_map):
    enrolls = {}
    for (duration, key), session_key in enrollment_key_map.items():
        enrolls[(duration, key)] = int(st.session_state.get(session_key, 0))
    enrolls_special = {
        "prop_num": int(st.session_state.get("iscr_prop", 0)),
        "sviluppo_num": int(st.session_state.get("iscr_sviluppo", 0)),
        "musica_in_fasce_num": int(st.session_state.get("iscr_fasce", 0)),
        "solo_solfeggio_num": int(st.session_state.get("iscr_solo_solfeggio", 0)),
    }
    return enrolls, enrolls_special


def compute_totals_from_state(num_lessons=LESSONS_PER_PACKAGE):
    enrolls, specials = read_enrollments_from_state(enrollment_keys)

    # -----------------------
    # RICAVI
    total_revenue = 0.0
    detail_rows = []
    for duration in [30, 45, 60]:
        for key, label in courses:
            n = enrolls.get((duration, key), 0)
            price_per_package = price_overrides.get(
                (duration, key), DEFAULT_PRICES_BY_MIN[duration]
            )
            revenue = price_per_package * n * (num_lessons / LESSONS_PER_PACKAGE)
            total_revenue += revenue
            detail_rows.append(
                {
                    "course_label": label,
                    "duration_min": duration,
                    "n_students": n,
                    "price_per_10_lezioni": price_per_package,
                    "revenue_for_package": revenue,
                }
            )

    # speciali
    if specials["sviluppo_num"] > 0:
        rev = (
            specials["sviluppo_num"] * svil_price * (num_lessons / LESSONS_PER_PACKAGE)
        )
        total_revenue += rev
        detail_rows.append(
            {
                "course_label": "Sviluppo musicalità",
                "duration_min": svil_duration,
                "n_students": specials["sviluppo_num"],
                "price_per_10_lezioni": svil_price,
                "revenue_for_package": rev,
            }
        )

    if specials["solo_solfeggio_num"] > 0:
        rev = (
            specials["solo_solfeggio_num"]
            * solo_solf_price
            * (num_lessons / LESSONS_PER_PACKAGE)
        )
        total_revenue += rev
        detail_rows.append(
            {
                "course_label": "Solo solfeggio",
                "duration_min": 60,
                "n_students": specials["solo_solfeggio_num"],
                "price_per_10_lezioni": solo_solf_price,
                "revenue_for_package": rev,
            }
        )

    # -----------------------
    # ORE PER PACCHETTO
    # 1) Individuali (strumento)
    individual_hours = 0.0
    for (duration, key), n in enrolls.items():
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf"):
            individual_hours += n * (duration / 60.0) * num_lessons

    # 2) Solfeggio in classe: diviso per durata
    solfeggio_class_count_by_duration = {}
    for duration in [30, 45, 60]:
        students = enrolls.get((duration, "fiato_solf"), 0) + enrolls.get(
            (duration, "arco_solf"), 0
        )
        if duration == 60:
            students += specials["solo_solfeggio_num"]
        class_count = ceil(students / min_students) if students > 0 else 0
        solfeggio_class_count_by_duration[duration] = class_count

    solfeggio_class_hours = sum(
        count * (d / 60.0) * num_lessons
        for d, count in solfeggio_class_count_by_duration.items()
    )

    # 3) Altri corsi in classe: propedeutica, sviluppo, musica in fasce
    other_class_hours = 0.0
    if specials["prop_num"] > 0:
        other_class_hours += (
            ceil(specials["prop_num"] / min_students)
            * (prop_duration / 60.0)
            * num_lessons
        )
    if specials["sviluppo_num"] > 0:
        other_class_hours += (
            ceil(specials["sviluppo_num"] / min_students)
            * (svil_duration / 60.0)
            * num_lessons
        )
    if specials["musica_in_fasce_num"] > 0:
        other_class_hours += (
            ceil(specials["musica_in_fasce_num"] / min_students)
            * (fasce_duration / 60.0)
            * num_lessons
        )

    total_package_hours = individual_hours + solfeggio_class_hours + other_class_hours

    # -----------------------
    # ORE SETTIMANALI
    weekly_individual_hours = 0.0
    for (duration, key), n in enrolls.items():
        if key in ("solo_fiato", "solo_arco", "fiato_solf", "arco_solf"):
            weekly_individual_hours += n * (duration / 60.0)

    weekly_solfeggio_hours = sum(
        count * (d / 60.0) for d, count in solfeggio_class_count_by_duration.items()
    )
    weekly_solfeggio_class_count_total = sum(solfeggio_class_count_by_duration.values())

    weekly_other_class_hours = 0.0
    if specials["prop_num"] > 0:
        weekly_other_class_hours += ceil(specials["prop_num"] / min_students) * (
            prop_duration / 60.0
        )
    if specials["sviluppo_num"] > 0:
        weekly_other_class_hours += ceil(specials["sviluppo_num"] / min_students) * (
            svil_duration / 60.0
        )
    if specials["musica_in_fasce_num"] > 0:
        weekly_other_class_hours += ceil(
            specials["musica_in_fasce_num"] / min_students
        ) * (fasce_duration / 60.0)

    weekly_total_hours = (
        weekly_individual_hours + weekly_solfeggio_hours + weekly_other_class_hours
    )

    # -----------------------
    # COSTI
    teacher_cost = hourly_teacher_cost * (individual_hours + other_class_hours)
    solfeggio_cost = hourly_teacher_cost * solfeggio_class_hours
    total_costs = teacher_cost + solfeggio_cost + other_fixed_costs
    deviation = total_revenue - total_costs

    teacher_cost_weekly = hourly_teacher_cost * (
        weekly_individual_hours + weekly_other_class_hours
    )
    solfeggio_cost_weekly = hourly_teacher_cost * weekly_solfeggio_hours
    total_costs_weekly = teacher_cost_weekly + solfeggio_cost_weekly + other_fixed_costs

    saturation_pct = (
        (weekly_total_hours / total_available_hours) * 100
        if total_available_hours > 0
        else 0.0
    )

    # -----------------------
    # Dizionario solfeggio per durata (compatibilità)
    solfeggio_students_by_duration = {
        30: enrolls.get((30, "fiato_solf"), 0) + enrolls.get((30, "arco_solf"), 0),
        45: enrolls.get((45, "fiato_solf"), 0) + enrolls.get((45, "arco_solf"), 0),
        60: enrolls.get((60, "fiato_solf"), 0)
        + enrolls.get((60, "arco_solf"), 0)
        + specials["solo_solfeggio_num"],
        "total": sum(solfeggio_class_count_by_duration.values()),
    }

    return {
        # pacchetto
        "num_lessons": num_lessons,
        "total_revenue": total_revenue,
        "individual_hours": individual_hours,
        "solfeggio_class_hours": solfeggio_class_hours,
        "solfeggio_class_count_by_duration": solfeggio_class_count_by_duration,
        "other_class_hours": other_class_hours,
        "total_hours": total_package_hours,
        "teacher_cost": teacher_cost,
        "solfeggio_cost": solfeggio_cost,
        "other_fixed_costs": other_fixed_costs,
        "total_costs": total_costs,
        "deviation": deviation,
        "detail_rows": detail_rows,
        # settimanali
        "weekly_individual_hours": weekly_individual_hours,
        "weekly_solfeggio_hours": weekly_solfeggio_hours,
        "weekly_other_class_hours": weekly_other_class_hours,
        "weekly_total_hours": weekly_total_hours,
        "weekly_teacher_cost": teacher_cost_weekly,
        "weekly_solfeggio_cost": solfeggio_cost_weekly,
        "weekly_total_costs": total_costs_weekly,
        "saturation_pct": saturation_pct,
        "solfeggio_students_by_duration": solfeggio_students_by_duration,
        "weekly_solfeggio_class_count_total": weekly_solfeggio_class_count_total,
    }
