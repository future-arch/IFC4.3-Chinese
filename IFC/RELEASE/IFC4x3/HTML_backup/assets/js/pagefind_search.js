// IFC 4.3 中文版 - Pagefind 客户端搜索集成
// 使用 Pagefind JavaScript API: https://pagefind.app/docs/api/

(function() {
    'use strict';

    // 等待 DOM 加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSearch);
    } else {
        initSearch();
    }

    let pagefind = null;

    function initSearch() {
        // 查找搜索表单
        const searchForm = document.querySelector('form.search');
        if (!searchForm) {
            console.log('未找到搜索表单');
            return;
        }

        const searchInput = searchForm.querySelector('input[name="query"]');
        if (!searchInput) {
            console.log('未找到搜索输入框');
            return;
        }

        // 阻止表单默认提交行为
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch(searchInput.value.trim());
        });

        console.log('搜索功能已初始化');
    }

    async function performSearch(query) {
        if (!query) {
            return;
        }

        console.log('搜索:', query);

        // 显示加载状态
        showSearchLoading();

        try {
            // 初始化 Pagefind (如果还没有初始化)
            if (!pagefind) {
                console.log('加载 Pagefind...');
                // 使用动态 import 加载 Pagefind
                pagefind = await import('/IFC/RELEASE/IFC4x3/HTML/pagefind/pagefind.js');

                // 配置选项 - 优化排名算法以提升精确匹配的权重
                await pagefind.options({
                    bundlePath: '/IFC/RELEASE/IFC4x3/HTML/pagefind/',
                    ranking: {
                        termSimilarity: 1.0,      // 提升精确匹配的排名(默认1.0,最大1.0)
                        termFrequency: 0.9,       // 略微降低词频权重(默认1.0)
                        pageLength: 0.5,          // 降低页面长度影响(默认0.75)
                        termSaturation: 1.0       // 降低词饱和度影响(默认1.4)
                    }
                });

                console.log('Pagefind 加载完成');
            }

            // 执行搜索
            console.log('执行搜索:', query);
            const search = await pagefind.search(query);

            console.log('搜索结果:', search.results.length);

            if (search.results.length === 0) {
                showNoResults(query);
                return;
            }

            // 显示搜索结果
            await displaySearchResults(search.results, query);

        } catch (error) {
            console.error('搜索失败:', error);
            showSearchError(error);
        }
    }

    function showSearchLoading() {
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div class="search-loading" style="text-align: center; padding: 50px;">
                    <h2>搜索中...</h2>
                    <p>请稍候</p>
                </div>
            `;
        }
    }

    function showNoResults(query) {
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <h2>搜索</h2>
                <form method="get" action="" style="margin-bottom: 20px;">
                    <input type="text" name="query" value="${escapeHtml(query)}" style="padding: 5px; width: 300px;"/>
                    <input type="submit" value="搜索" style="padding: 5px 15px;"/>
                </form>
                <ul style="list-style: none; padding: 0;">
                    <li><span>未找到与您的查询匹配的结果</span></li>
                </ul>
            `;

            // 重新绑定搜索表单
            const newForm = mainContent.querySelector('form');
            if (newForm) {
                newForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const newQuery = newForm.querySelector('input[name="query"]').value.trim();
                    if (newQuery) {
                        performSearch(newQuery);
                    }
                });
            }
        }
    }

    function showSearchError(error) {
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div class="search-error" style="padding: 20px; color: red;">
                    <h1>搜索错误</h1>
                    <p>抱歉,搜索功能暂时不可用。</p>
                    <p>错误信息: ${escapeHtml(error.message)}</p>
                    <p>请稍后再试,或<a href="/">返回首页</a>。</p>
                </div>
            `;
        }
    }

    async function displaySearchResults(results, query) {
        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        // 批量加载所有结果数据
        const resultDataPromises = results.map(r => r.data());
        const resultDataList = await Promise.all(resultDataPromises);

        // 客户端排序 - 优先显示标题中包含搜索词的结果
        const queryLower = query.toLowerCase();
        const sortedResults = resultDataList.sort((a, b) => {
            const titleA = (a.meta.title || extractTitleFromUrl(a.url)).toLowerCase();
            const titleB = (b.meta.title || extractTitleFromUrl(b.url)).toLowerCase();

            // 优先级1: 标题完全匹配
            const exactMatchA = titleA === queryLower ? 1 : 0;
            const exactMatchB = titleB === queryLower ? 1 : 0;
            if (exactMatchA !== exactMatchB) return exactMatchB - exactMatchA;

            // 优先级2: 标题以搜索词开头(如 IfcWall 搜索 "wall")
            const startsWithA = titleA.startsWith(queryLower) ? 1 : 0;
            const startsWithB = titleB.startsWith(queryLower) ? 1 : 0;
            if (startsWithA !== startsWithB) return startsWithB - startsWithA;

            // 优先级3: 标题包含搜索词(如 IfcWallStandardCase 搜索 "wall")
            const containsA = titleA.includes(queryLower) ? 1 : 0;
            const containsB = titleB.includes(queryLower) ? 1 : 0;
            if (containsA !== containsB) return containsB - containsA;

            // 优先级4: 保持 Pagefind 原始排序
            return 0;
        });

        // 限制显示前 30 个结果(参考英文版)
        const maxResults = Math.min(sortedResults.length, 30);

        let html = `
            <style>
                /* 自定义搜索结果中高亮标记的样式 */
                mark {
                    background-color: #e0e0e0;  /* 灰色背景 */
                    color: #000;                 /* 黑色文字 */
                    padding: 1px 2px;
                    border-radius: 2px;
                }
            </style>
            <h2>搜索</h2>
            <form method="get" action="" style="margin-bottom: 20px;">
                <input type="text" name="query" value="${escapeHtml(query)}" style="padding: 5px; width: 300px;"/>
                <input type="submit" value="搜索" style="padding: 5px 15px;"/>
            </form>
            <ul style="list-style: none; padding: 0;">
        `;

        for (let i = 0; i < maxResults; i++) {
            const data = sortedResults[i];

            // 提取标题(从 meta 或 URL 中)
            const title = data.meta.title || extractTitleFromUrl(data.url);

            html += `
                <li style="margin-bottom: 15px;">
                    <a href="${data.url}" style="font-weight: bold; color: #0066cc; text-decoration: none;">
                        ${escapeHtml(title)}
                    </a>
                    <span style="display: block; margin-top: 5px; color: #333; line-height: 1.5;">
                        ${data.excerpt}
                    </span>
                </li>
            `;
        }

        // 如果没有结果
        if (sortedResults.length === 0) {
            html += `<li><span>未找到与您的查询匹配的结果</span></li>`;
        }

        html += `</ul>`;

        if (sortedResults.length > maxResults) {
            html += `<p style="color: #666; font-style: italic;">显示前 ${maxResults} 个结果,共 ${sortedResults.length} 个匹配项</p>`;
        }

        mainContent.innerHTML = html;

        // 重新绑定搜索表单
        const newForm = mainContent.querySelector('form');
        if (newForm) {
            newForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const newQuery = newForm.querySelector('input[name="query"]').value.trim();
                if (newQuery) {
                    performSearch(newQuery);
                }
            });
        }
    }

    function extractTitleFromUrl(url) {
        // 从 URL 中提取文件名作为标题
        // 例如: /IFC/RELEASE/IFC4x3/HTML/lexical/IfcWall.htm -> IfcWall
        const match = url.match(/\/([^\/]+)\.htm?$/);
        return match ? match[1] : url;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
