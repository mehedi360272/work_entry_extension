# -*- coding: utf-8 -*-
from datetime import datetime, time
from collections import defaultdict

from odoo import models


class AzkPlanningSyncWizardInherit(models.TransientModel):
    _inherit = "azk.planning.sync.wizard"

    def action_sync(self):
        self.ensure_one()
        print("\n==============================")
        print("ACTION_SYNC CLICKED")
        print("==============================")

        # ✅ ALWAYS initialize (so never UnboundLocalError)
        processed_employees = self.env["hr.employee"]  # empty recordset
        overall_min = None
        overall_max = None

        # 1) run sync and get summary
        start_dt = datetime.combine(self.date_start, time.min)
        end_dt = datetime.combine(self.date_end, time.max)

        print("SYNC WINDOW:", start_dt, "->", end_dt)
        print("EMPLOYEE IDS (wizard):", self.employee_ids.ids)
        print("TOLERANCE (minutes):", self.tolerance_minutes)

        summary = self.env["azk.report.daily.attendance.filtered"]._sync_from_filtered(
            start_dt,
            end_dt,
            employee_ids=self.employee_ids.ids,
        )
        print("SYNC SUMMARY:", summary)

        # 2) ONLY processed slots -> generate work entries from those windows
        slot_ids = summary.get("slot_ids") or []
        print("SLOT IDS:", slot_ids)

        if slot_ids:
            Slot = self.env["planning.slot"].sudo()
            slots = Slot.browse(slot_ids).exists()
            print("SLOTS FOUND:", len(slots))

            emp_windows = defaultdict(lambda: {"min": None, "max": None})

            for s in slots:
                emp = getattr(s, "employee_id", False)
                print(
                    f"SLOT id={s.id} | emp={(emp.id if emp else None)} "
                    f"| start={s.start_datetime} | end={s.end_datetime}"
                )

                if not emp or not s.start_datetime or not s.end_datetime:
                    print("  -> SKIP: missing emp/start/end")
                    continue

                w = emp_windows[emp.id]
                w["min"] = s.start_datetime if not w["min"] else min(w["min"], s.start_datetime)
                w["max"] = s.end_datetime if not w["max"] else max(w["max"], s.end_datetime)

                overall_min = w["min"] if not overall_min else min(overall_min, w["min"])
                overall_max = w["max"] if not overall_max else max(overall_max, w["max"])

            print("EMP WINDOWS:", dict(emp_windows))

            WorkEntry = self.env["hr.work.entry"].sudo()
            processed_employees = self.env["hr.employee"].browse(list(emp_windows.keys())).exists()
            print("EMPLOYEES FOR GENERATE:", processed_employees.ids)

            # ✅ employee-wise generate (tight window)
            if hasattr(WorkEntry, "_generate_work_entries"):
                print("USING: hr.work.entry._generate_work_entries()")
                for emp in processed_employees:
                    w = emp_windows[emp.id]
                    print(f"GENERATE FOR emp={emp.id} window={w['min']} -> {w['max']}")
                    if w["min"] and w["max"]:
                        WorkEntry._generate_work_entries(w["min"], w["max"], employees=emp)
                        print("  -> CALLED _generate_work_entries ✅")
            else:
                print("FALLBACK: hr.employee._generate_work_entries()")
                for emp in processed_employees:
                    w = emp_windows[emp.id]
                    print(f"GENERATE FOR emp={emp.id} window={w['min']} -> {w['max']}")
                    if w["min"] and w["max"] and hasattr(emp, "_generate_work_entries"):
                        emp._generate_work_entries(w["min"], w["max"])
                        print("  -> CALLED emp._generate_work_entries ✅")

        print("WORK ENTRY PART FINISHED")
        print("==============================\n")

        # ✅✅ 3) regenerate AFTER finish (fallback: wizard date range + wizard employee_ids)
        regen_employees = processed_employees or self.employee_ids
        regen_min = overall_min or datetime.combine(self.date_start, time.min)
        regen_max = overall_max or datetime.combine(self.date_end, time.max)

        print(
            "REGEN DEBUG -> processed_employees:",
            processed_employees.ids,
            "| wizard employees:",
            self.employee_ids.ids,
            "| overall_min:",
            overall_min,
            "| overall_max:",
            overall_max,
        )

        if regen_employees and regen_min and regen_max:
            print(f"REGENERATE AFTER FINISH: employees={regen_employees.ids} window={regen_min} -> {regen_max}")

            wiz = self.env["hr.work.entry.regeneration.wizard"].sudo().create({
                "date_from": regen_min.date(),
                "date_to": regen_max.date(),
                "employee_ids": [(6, 0, regen_employees.ids)],
            })

            # skip validations for automation
            wiz = wiz.with_context(work_entry_skip_validation=True)
            wiz.regenerate_work_entries()
            print("  -> CALLED wizard.regenerate_work_entries ✅")
        else:
            print("REGENERATE SKIPPED (no employees/window even after fallback)")

        # 4) show notification
        message = (
            f"Processed {summary.get('slots', 0)} planning shifts.\n"
            f"Created: {summary.get('created', 0)} | Updated: {summary.get('updated', 0)} | Skipped: {summary.get('skipped', 0)}"
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Planning Sync",
                "message": message,
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
