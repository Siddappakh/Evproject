import { expect, test } from "@playwright/test";

test("isolated user can register, seed factors, add categories, view dashboard, sign out and log in", async ({ page, request }) => {
  const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const email = `e2e.individual.${suffix}@example.com`;
  const password = "GreenTrack-E2E-2026!";

  await page.goto("/register/individual");
  await page.getByLabel("Full name").fill("E2E Individual");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.getByLabel("Workspace name").fill(`E2E Personal ${suffix}`);
  await page.getByLabel("Personal workspace").fill(`E2E Personal ${suffix}`);
  await page.getByLabel("Reporting region").fill("India");
  await page.getByRole("button", { name: "Finish setup" }).click();
  await expect(page).toHaveURL(/\/individual\/dashboard$/);

  await page.goto("/individual/activity");
  await page.getByRole("button", { name: "Initialize Reference Factors" }).click();
  await expect(page.getByText(/standard emission factors initialized|reference values ready/i)).toBeVisible();

  await page.getByLabel("Activity Description *").fill("E2E monthly electricity");
  await page.getByLabel("Quantity *").fill("100");
  await page.getByLabel("Unit *").selectOption("kWh");
  await page.getByLabel("Factor Definition").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Calculate and Save Activity" }).click();
  await expect(page.getByText(/Calculation Preview|Activity Saved|emissions/i).first()).toBeVisible();

  await page.goto("/individual/dashboard");
  await expect(page.getByText(/Dashboard|emissions/i).first()).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/");

  await page.goto("/auth/individual");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/individual\/dashboard$/);

  const unauthenticated = await request.get("http://127.0.0.1:8001/api/activities");
  expect(unauthenticated.status()).toBe(401);
});
