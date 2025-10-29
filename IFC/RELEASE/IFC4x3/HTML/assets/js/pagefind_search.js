// IFC 4.3 中文版 - Pagefind 客户端搜索集成 (简化版)

(function() {
    'use strict';

    // 等待 DOM 加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSearch);
    } else {
        initSearch();
    }

    let pagefindInstance = null;

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
            if (!pagefindInstance) {
                console.log('初始化 Pagefind...');
                // 动态加载 Pagefind
                await loadPagefindScript();

                // 创建 Pagefind 实例
                pagefindInstance = new window.PagefindInstance({
                    basePath: '/IFC/RELEASE/IFC4x3/HTML/pagefind/'
                });

                // 初始化 (自动检测语言)
                await pagefindInstance.init('zh-cn', { load_wasm: true });
                console.log('Pagefind 初始化完成');
            }

            // 执行搜索
            console.log('执行搜索:', query);
            const search = await pagefindInstance.search(query);

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

    function loadPagefindScript() {
        return new Promise((resolve, reject) => {
            // 如果已经加载,直接返回
            if (window.PagefindInstance) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = '/IFC/RELEASE/IFC4x3/HTML/pagefind/pagefind.js';

            script.onload = function() {
                console.log('Pagefind 脚本加载成功');
                // 等待一小会儿确保全局对象可用
                setTimeout(resolve, 100);
            };

            script.onerror = function() {
                reject(new Error('无法加载 Pagefind 脚本'));
            };

            document.head.appendChild(script);
        });
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
                <div class="search-no-results" style="padding: 20px;">
                    <h1>搜索结果</h1>
                    <p>未找到与 "<strong>${escapeHtml(query)}</strong>" 相关的结果。</p>
                    <p>建议：</p>
                    <ul>
                        <li>检查拼写是否正确</li>
                        <li>尝试使用不同的关键词</li>
                        <li>使用更通用的搜索词</li>
                    </ul>
                </div>
            `;
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

        let html = `
            <h1>搜索结果</h1>
            <p>找到 <strong>${results.length}</strong> 个与 "<strong>${escapeHtml(query)}</strong>" 相关的结果：</p>
            <div class="search-results" style="margin-top: 20px;">
        `;

        // 限制显示前 30 个结果
        const maxResults = Math.min(results.length, 30);

        for (let i = 0; i < maxResults; i++) {
            const result = results[i];

            try {
                const data = await result.data();

                html += `
                    <div class="search-result-item" style="margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee;">
                        <h3 style="margin-bottom: 10px;">
                            <a href="${data.url}">${escapeHtml(data.meta.title || data.url)}</a>
                        </h3>
                        <p style="color: #666; margin-bottom: 10px;">
                            ${data.excerpt}
                        </p>
                        <p style="font-size: 0.9em; color: #999;">
                            <a href="${data.url}" style="text-decoration: none;">${data.url}</a>
                        </p>
                    </div>
                `;
            } catch (err) {
                console.error('加载结果数据失败:', err);
            }
        }

        html += `</div>`;

        if (results.length > maxResults) {
            html += `<p style="color: #666;">...还有 ${results.length - maxResults} 个结果未显示</p>`;
        }

        mainContent.innerHTML = html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
