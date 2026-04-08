const { chromium } = require('playwright');

const urls = [
  { name: '火山引擎 Coding Plan', url: 'https://www.volcengine.com/activity/codingplan' },
  { name: '火山引擎 套餐概览', url: 'https://www.volcengine.com/docs/82379/1925114' },
  { name: '移动云 Coding Plan', url: 'https://ecloud.10086.cn/portal/act/codingplan' },
  { name: '京东云 Coding Plan', url: 'https://docs.jdcloud.com/cn/jdaip/Specialoffer' },
  { name: '联通云 Coding Plan', url: 'https://www.cucloud.cn/activity/kickoffseason.html' },
];

async function fetchPage(urlInfo) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`\n=== 正在获取: ${urlInfo.name} ===`);
  console.log(`URL: ${urlInfo.url}`);

  try {
    await page.goto(urlInfo.url, { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    await page.waitForTimeout(3000);

    const title = await page.title();
    console.log(`页面标题: ${title}`);

    const bodyText = await page.evaluate(() => document.body.innerText);
    
    console.log(`\n--- 页面内容摘要 (前500字符): ---`);
    console.log(bodyText.substring(0, 500));
    
    const pricePatterns = ['元/月', '¥', '价格', '套餐', '优惠', '免费', 'API', '模型'];
    const foundPatterns = pricePatterns.filter(p => bodyText.includes(p));
    console.log(`\n--- 找到的相关关键词: ---`);
    console.log(foundPatterns.join(', '));

    const priceMatch = bodyText.match(/(\d+\.?\d*)\s*元/);
    if (priceMatch) {
      console.log(`\n找到价格: ${priceMatch[0]}`);
    }

    return {
      name: urlInfo.name,
      url: urlInfo.url,
      success: true,
      title: title,
      content: bodyText.substring(0, 2000),
      foundPatterns
    };

  } catch (error) {
    console.error(`获取失败: ${error.message}`);
    return {
      name: urlInfo.name,
      url: urlInfo.url,
      success: false,
      error: error.message
    };
  } finally {
    await browser.close();
  }
}

async function main() {
  console.log('========================================');
  console.log('使用 Playwright 无头浏览器获取 JavaScript 渲染页面');
  console.log('========================================');

  const results = [];
  for (const urlInfo of urls) {
    const result = await fetchPage(urlInfo);
    results.push(result);
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  console.log('\n\n========================================');
  console.log('获取结果汇总');
  console.log('========================================');

  for (const r of results) {
    console.log(`\n${r.name}: ${r.success ? '✅ 成功' : '❌ 失败'}`);
    if (r.success) {
      console.log(`  标题: ${r.title}`);
      if (r.foundPatterns) {
        console.log(`  关键词: ${r.foundPatterns.join(', ')}`);
      }
    } else {
      console.log(`  错误: ${r.error}`);
    }
  }

  const fs = require('fs');
  fs.writeFileSync('fetch-results.json', JSON.stringify(results, null, 2));
  console.log('\n\n结果已保存到 fetch-results.json');
}

main().catch(console.error);
