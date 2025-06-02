# QDrant Loader Visual Assets

This directory contains all visual assets for the QDrant Loader project, including logos, icons, favicons, and branding materials.

## 🎨 **Logo Collection**

### Main Logos

- **`logos/qdrant-loader-logo.svg`** - Full logo with text and tagline (400×120px)
  - Use for: Marketing materials, documentation headers, presentations
  - Features: Animated data streams, gradient styling, enterprise tagline

- **`logos/qdrant-loader-logo-horizontal.svg`** - Compact horizontal logo (300×60px)
  - Use for: Navigation bars, headers, compact spaces
  - Features: Streamlined design, perfect for web navigation

### Icon Collection

- **`icons/qdrant-loader-icon.svg`** - Animated standalone icon (100×100px)
  - Use for: App icons, social media, animated contexts
  - Features: Pulsing data streams, gradient background

- **`icons/qdrant-loader-icon-static.svg`** - Static standalone icon (100×100px)
  - Use for: Favicons, print materials, static contexts
  - Features: Clean design without animations

## 📱 **Favicon Suite**

Complete favicon collection generated from the static icon:

### Standard Favicons

- `favicons/favicon.ico` - Legacy ICO format (16×16, 32×32, 48×48)
- `favicons/favicon-16x16.png` - Standard browser favicon
- `favicons/favicon-32x32.png` - High-DPI browser favicon

### Mobile & App Icons

- `favicons/apple-touch-icon.png` - iOS home screen icon (180×180)
- `favicons/android-chrome-192x192.png` - Android Chrome icon
- `favicons/android-chrome-512x512.png` - Android Chrome high-res icon

### Additional Sizes

- `favicons/favicon-48x48.png` - Windows taskbar
- `favicons/favicon-64x64.png` - Desktop shortcuts
- `favicons/favicon-96x96.png` - Android Chrome
- `favicons/favicon-128x128.png` - Chrome Web Store

## 🌐 **Web Manifest**

- **`site.webmanifest`** - PWA manifest for installable web app
  - Defines app name, icons, theme colors
  - Enables "Add to Home Screen" functionality
  - Supports both PNG and SVG icons

## 🎨 **Design System**

### Color Palette

```css
--primary-color: #667eea    /* Primary brand blue */
--secondary-color: #764ba2  /* Secondary purple */
--success-color: #48bb78    /* Success green */
--info-color: #4299e1      /* Info blue */
```

### Design Principles

- **Modern & Professional**: Clean lines, gradient styling
- **Data-Focused**: Rocket/loader metaphor with data streams
- **Enterprise-Ready**: Sophisticated color palette
- **Scalable**: Vector-based for all sizes
- **Animated**: Subtle animations for digital contexts

## 🛠️ **Usage Guidelines**

### Logo Usage

```html
<!-- Navigation bar -->
<img src="assets/logos/qdrant-loader-logo-horizontal.svg" alt="QDrant Loader" height="40">

<!-- Hero section -->
<img src="assets/logos/qdrant-loader-logo.svg" alt="QDrant Loader" height="120">

<!-- App icon -->
<img src="assets/icons/qdrant-loader-icon.svg" alt="QDrant Loader" width="64" height="64">
```

### Favicon Implementation

```html
<!-- Standard favicons -->
<link rel="icon" type="image/x-icon" href="assets/favicons/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="assets/favicons/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="assets/favicons/favicon-32x32.png">

<!-- Mobile icons -->
<link rel="apple-touch-icon" sizes="180x180" href="assets/favicons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="192x192" href="assets/favicons/android-chrome-192x192.png">
<link rel="icon" type="image/png" sizes="512x512" href="assets/favicons/android-chrome-512x512.png">

<!-- Web manifest -->
<link rel="manifest" href="assets/site.webmanifest">
<meta name="theme-color" content="#667eea">
```

## 🔧 **Generation Scripts**

### Favicon Generation

```bash
# Install dependencies
pip install cairosvg pillow

# Generate all favicon sizes
python generate_favicons.py
```

The `generate_favicons.py` script automatically:

- Converts SVG to PNG in all required sizes
- Generates ICO file for legacy browsers
- Creates Apple Touch Icon and Android Chrome icons
- Optimizes for different platforms and use cases

## 📋 **File Inventory**

### Logos (2 files)

- qdrant-loader-logo.svg (full logo with tagline)
- qdrant-loader-logo-horizontal.svg (compact navigation logo)

### Icons (2 files)

- qdrant-loader-icon.svg (animated version)
- qdrant-loader-icon-static.svg (static version)

### Favicons (10 files)

- favicon.ico (legacy format)
- favicon-16x16.png through favicon-128x128.png (various sizes)
- apple-touch-icon.png (iOS)
- android-chrome-192x192.png & android-chrome-512x512.png (Android)

### Configuration (1 file)

- site.webmanifest (PWA configuration)

### Scripts (1 file)

- generate_favicons.py (favicon generation utility)

## 🎯 **Brand Applications**

### Digital

- ✅ Website headers and navigation
- ✅ Documentation sites
- ✅ GitHub repository
- ✅ PyPI package pages
- ✅ Social media profiles

### Development

- ✅ IDE integration (MCP server)
- ✅ CLI tool branding
- ✅ Error messages and logs
- ✅ Configuration files

### Marketing

- ✅ Presentations and demos
- ✅ Blog posts and articles
- ✅ Conference materials
- ✅ Email signatures

---

**Note**: All assets are optimized for web use and maintain consistent branding across all QDrant Loader touchpoints. The design emphasizes the project's focus on data loading, vector databases, and enterprise-ready solutions.
