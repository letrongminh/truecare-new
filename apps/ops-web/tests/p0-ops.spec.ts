import { expect, test } from "@playwright/test";

const routes = [
  ["admissions", "ops-admissions-screen"],
  ["commission", "ops-commission-screen"],
  ["complaints", "ops-complaints-screen"],
  ["network-health", "ops-network-health-screen"],
  ["growth-ekyc", "ops-growth-ekyc-screen"],
  ["audit-log", "ops-audit-log-screen"]
] as const;

test.describe("TrueCare Ops P0 routes", () => {
  for (const [route, testId] of routes) {
    test(`${route} renders route state surface`, async ({ page }) => {
      await page.goto(`/#/${route}`);
      await expect(page.getByTestId("ops-shell")).toBeVisible();
      await expect(page.getByTestId(testId)).toBeVisible();
      await expect(page.getByTestId(`${testId.replace("-screen", "")}-retry`)).toBeVisible();
    });
  }
});
