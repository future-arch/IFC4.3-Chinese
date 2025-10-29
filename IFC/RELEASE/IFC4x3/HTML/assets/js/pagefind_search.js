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

                // 配置选项 (可选)
                await pagefind.options({
                    bundlePath: '/IFC/RELEASE/IFC4x3/HTML/pagefind/'
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

        // 限制显示前 30 个结果(参考英文版)
        const maxResults = Math.min(results.length, 30);

        let html = `
            <h2>搜索</h2>
            <form method="get" action="" style="margin-bottom: 20px;">
                <input type="text" name="query" value="${escapeHtml(query)}" style="padding: 5px; width: 300px;"/>
                <input type="submit" value="搜索" style="padding: 5px 15px;"/>
            </form>
            <ul style="list-style: none; padding: 0;">
        `;

        // 批量加载结果数据以提高性能
        const resultDataPromises = results.slice(0, maxResults).map(r => r.data());
        const resultDataList = await Promise.all(resultDataPromises);

        for (let i = 0; i < resultDataList.length; i++) {
            const data = resultDataList[i];

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
        if (resultDataList.length === 0) {
            html += `<li><span>未找到与您的查询匹配的结果</span></li>`;
        }

        html += `</ul>`;

        if (results.length > maxResults) {
            html += `<p style="color: #666; font-style: italic;">显示前 ${maxResults} 个结果,共 ${results.length} 个匹配项</p>`;
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
