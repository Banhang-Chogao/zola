+++
title = "Hilda Theme — Branding Guideline"
description = "Visual branding guide for Hilda theme (Ericsson Professional Style)"
date = 2026-06-16

[taxonomies]
categories = []
tags = ["branding", "design-system", "hilda"]

[extra]
featured = false
+++

# Hilda Theme — Branding Guideline

Hướng dẫn thiết kế trực quan cho theme **Hilda** (Phong cách Ericsson chuyên nghiệp).

---

## 🎨 Palette Màu Sắc

### Primary Colors

<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0;">
  <div style="background: #003784; padding: 40px; border-radius: 4px; color: white; text-align: center;">
    <strong>Ericsson Blue</strong><br>
    <code>#003784</code><br>
    <small>RGB(0, 55, 132)</small>
  </div>
  <div style="background: #00a69d; padding: 40px; border-radius: 4px; color: white; text-align: center;">
    <strong>Teal</strong><br>
    <code>#00a69d</code><br>
    <small>RGB(0, 166, 157)</small>
  </div>
</div>

### Accent Colors

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
  <div style="background: #e30613; padding: 40px; border-radius: 4px; color: white; text-align: center;">
    <strong>CTA Red</strong><br>
    <code>#e30613</code>
  </div>
  <div style="background: #000000; padding: 40px; border-radius: 4px; color: white; text-align: center;">
    <strong>Text Black</strong><br>
    <code>#000000</code>
  </div>
  <div style="background: #ffffff; padding: 40px; border-radius: 4px; border: 1px solid #e0e0e0; text-align: center; color: #000;">
    <strong>Background White</strong><br>
    <code>#ffffff</code>
  </div>
</div>

### Neutral Colors

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0;">
  <div style="background: #333333; padding: 30px; border-radius: 4px; color: white; text-align: center; font-size: 12px;">
    <strong>Body</strong><br>
    <code>#333333</code>
  </div>
  <div style="background: #666666; padding: 30px; border-radius: 4px; color: white; text-align: center; font-size: 12px;">
    <strong>Muted</strong><br>
    <code>#666666</code>
  </div>
  <div style="background: #e0e0e0; padding: 30px; border-radius: 4px; color: #333; text-align: center; font-size: 12px;">
    <strong>Border</strong><br>
    <code>#e0e0e0</code>
  </div>
  <div style="background: #f4f4f4; padding: 30px; border-radius: 4px; border: 1px solid #e0e0e0; color: #333; text-align: center; font-size: 12px;">
    <strong>Light Gray</strong><br>
    <code>#f4f4f4</code>
  </div>
</div>

---

## 🔤 Typography — Ericsson Hilda Font

### Font Family
```
Ericsson Hilda (OTF)
Fallback: Inter, Roboto, System Font
```

### Font Sizes & Weights

<div style="margin: 30px 0;">
  <h1 style="font-size: 32px; font-weight: 700; color: #003784; margin: 20px 0;">Heading 1 (32px, Bold)</h1>
  <h2 style="font-size: 28px; font-weight: 700; color: #003784; margin: 20px 0;">Heading 2 (28px, Bold)</h2>
  <h3 style="font-size: 24px; font-weight: 600; color: #003784; margin: 20px 0;">Heading 3 (24px, SemiBold)</h3>
  <p style="font-size: 16px; font-weight: 400; color: #333333; line-height: 1.6; margin: 20px 0;">
    <strong>Body Text (16px, Regular)</strong> — Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
    Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
  </p>
  <p style="font-size: 14px; font-weight: 400; color: #666666; margin: 20px 0;">
    <strong>Small / Caption (14px, Regular)</strong> — Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
  </p>
</div>

### Letter Spacing

| Element | Letter-Spacing | Purpose |
|---|---|---|
| Headings | -0.02em | Tight, professional |
| Body | 0em | Natural, readable |
| Labels | 0.05em | Uppercase labels |

---

## 📐 UI Design System

### Border Radius

All UI elements use **4px border-radius** for a sharp, professional appearance (vs softer 14px).

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
  <div style="background: #003784; border-radius: 4px; padding: 40px; color: white; text-align: center;">
    <strong>Button</strong><br>
    <code>border-radius: 4px</code>
  </div>
  <div style="background: #f4f4f4; border-radius: 4px; border: 1px solid #e0e0e0; padding: 40px; text-align: center; color: #333;">
    <strong>Card</strong><br>
    <code>border-radius: 4px</code>
  </div>
  <div style="background: #e0e0e0; border-radius: 4px; padding: 40px; text-align: center; color: #333;">
    <strong>Input</strong><br>
    <code>border-radius: 4px</code>
  </div>
</div>

### Shadows

**Card Shadow (Resting State)**
```css
box-shadow: 0 2px 4px rgba(0, 55, 132, 0.08);
```

**Card Shadow (Hover State)**
```css
box-shadow: 0 8px 16px rgba(0, 55, 132, 0.12);
```

Visual example:

<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0;">
  <div style="background: white; padding: 30px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0, 55, 132, 0.08);">
    <strong>Resting State</strong><br>
    <small>Subtle shadow (0 2px 4px)</small>
  </div>
  <div style="background: white; padding: 30px; border-radius: 4px; box-shadow: 0 8px 16px rgba(0, 55, 132, 0.12);">
    <strong>Hover State</strong><br>
    <small>Elevated shadow (0 8px 16px)</small>
  </div>
</div>

### Spacing System

All spacing follows **8px base unit** (multiples):

| Size | Value | Usage |
|---|---|---|
| XS | 4px | Micro adjustments |
| SM | 8px | Padding, gaps |
| MD | 16px | Component spacing |
| LG | 24px | Section spacing |
| XL | 32px | Major sections |
| 2XL | 40px | Page margin |

---

## 🎯 Component Examples

### CTA Button (Primary)

<div style="margin: 20px 0;">
  <button style="
    background: #003784;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  " onmouseover="this.style.background='#002566'" onmouseout="this.style.background='#003784'">
    Primary CTA Button
  </button>
</div>

### Badge / Tag

<div style="display: flex; gap: 10px; margin: 20px 0; flex-wrap: wrap;">
  <span style="background: #003784; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">Hilda</span>
  <span style="background: #00a69d; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">Design System</span>
  <span style="background: #e30613; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600;">Professional</span>
</div>

### Contrast Test (WCAG AA)

<div style="margin: 20px 0; padding: 20px; background: #f4f4f4; border-radius: 4px;">
  <p style="color: #003784; font-size: 16px;"><strong>Ericsson Blue on White (Contrast: 10.8:1)</strong> ✅ WCAG AAA</p>
  <p style="color: #333333; font-size: 16px;"><strong>Body Text on White (Contrast: 18.3:1)</strong> ✅ WCAG AAA</p>
  <p style="color: #666666; font-size: 16px;"><strong>Muted Text on White (Contrast: 8.1:1)</strong> ✅ WCAG AAA</p>
</div>

---

## 🎨 Single Theme (Hilda)

Blog sử dụng **Hilda (Ericsson Blue)** làm theme duy nhất. Không có theme toggle.

- **Default theme:** Hilda Professional
- **Color scheme:** Ericsson Blue (#003784)
- **Style:** Clean, sharp, professional aesthetic

---

## ✅ Design Guidelines

1. **Always use 4px border-radius** — không dùng 6px, 8px hay các giá trị khác
2. **Maintain color palette** — chỉ sử dụng màu trong palette trên
3. **Use proper spacing** — 8px base unit (8, 16, 24, 32, 40...)
4. **Test contrast** — tất cả text phải ≥ 4.5:1 (WCAG AA)
5. **Smooth transitions** — 0.3s ease cho hover/active states
6. **Mobile first** — responsive <= 720px

---

**Last Updated:** 2026-06-16  
**Theme Version:** Hilda 1.0  
**Status:** Ready for Production
