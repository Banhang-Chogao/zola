const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

(async () => {
    try {
        console.log('🚀 Starting screenshot capture...\n');

        const browser = await puppeteer.launch({
            executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        const htmlPath = path.join(__dirname, 'blog-layout-left-sidebar.html');
        const htmlUrl = `file://${htmlPath}`;

        console.log(`📄 Loading: ${htmlUrl}\n`);

        // Screenshot 1: Desktop (1920x1080)
        console.log('📸 Capturing Desktop (1920×1080)...');
        const desktopPage = await browser.newPage();
        await desktopPage.setViewport({ width: 1920, height: 1080 });
        await desktopPage.goto(htmlUrl, { waitUntil: 'networkidle2' });
        await desktopPage.screenshot({
            path: path.join(__dirname, 'screenshot-left-sidebar-desktop.png'),
            fullPage: true
        });
        console.log('✅ Desktop screenshot saved: screenshot-left-sidebar-desktop.png');
        await desktopPage.close();

        // Screenshot 2: Mobile (375x812)
        console.log('\n📱 Capturing Mobile (375×812 - iPhone SE)...');
        const mobilePage = await browser.newPage();
        await mobilePage.setViewport({ width: 375, height: 812 });
        await mobilePage.goto(htmlUrl, { waitUntil: 'networkidle2' });
        await mobilePage.screenshot({
            path: path.join(__dirname, 'screenshot-left-sidebar-mobile.png'),
            fullPage: true
        });
        console.log('✅ Mobile screenshot saved: screenshot-left-sidebar-mobile.png');
        await mobilePage.close();

        await browser.close();

        console.log('\n' + '='.repeat(50));
        console.log('✨ All screenshots captured successfully!');
        console.log('='.repeat(50));
        console.log(`📂 Location: ${__dirname}`);
        console.log('\n📋 Files created:');
        console.log('   1. screenshot-left-sidebar-desktop.png (1920×1080)');
        console.log('   2. screenshot-left-sidebar-mobile.png (375×812)');
        console.log('\n✅ You can now view the layout in these PNG files!');
    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
})();
