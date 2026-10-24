import { expect, test } from '@playwright/test'

test('register, scan pasted code, see verified findings with citations and patch', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`
  await page.goto('/login')
  await page.getByRole('button', { name: 'No account? Register' }).click()
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('correct-horse-battery')
  await page.getByRole('button', { name: 'Register' }).click()

  await expect(page.getByRole('heading', { name: 'New scan' })).toBeVisible()
  await page.getByLabel('New project name').fill('e2e project')
  await page.getByRole('button', { name: 'Scan', exact: true }).click()

  await expect(page.getByText('COMPLETED')).toBeVisible({ timeout: 90_000 })
  await expect(page.getByText(/verified finding/)).toBeVisible()
  await expect(page.getByText('Meta.index_together').first()).toBeVisible()
  await expect(page.locator('.cites a').first()).toHaveAttribute('href', /docs\.djangoproject\.com/)

  await page.getByText('django.utils.timezone.utc').first().click()
  await expect(page.locator('.diff .add').first()).toBeVisible()

  await page.getByRole('link', { name: 'History' }).click()
  await expect(page.getByRole('heading', { name: 'Scan history' })).toBeVisible()
  await page.getByRole('link', { name: 'Compare systems' }).click()
  await expect(page.getByRole('heading', { name: 'Compare systems' })).toBeVisible()
})
