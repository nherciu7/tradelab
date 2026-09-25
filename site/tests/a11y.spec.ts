// WCAG 2 AA (axe-core), including colour contrast, in light and dark mode.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { PAGES } from "./helpers";

for (const scheme of ["light", "dark"] as const) {
  for (const page of PAGES) {
    test(`WCAG AA, ${scheme}: /${page}`, async ({ page: p }) => {
      await p.emulateMedia({ colorScheme: scheme });
      await p.goto(page);
      await p.locator("details.data-table").evaluateAll((els) => els.forEach((d) => d.setAttribute("open", "")));
      const r = await new AxeBuilder({ page: p }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      expect(r.violations.map((v) => `${v.id}: ${v.nodes.length} x ${v.nodes[0]?.target.join(" ")} (${v.help})`)).toEqual([]);
    });
  }
}
