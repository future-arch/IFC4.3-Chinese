// IFC 4.3 中文版 - Pagefind 客户端搜索集成

(function() {
    'use strict';

    // 等待 DOM 加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSearch);
    } else {
        initSearch();
    }

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

        // 实时搜索建议（可选）
        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            if (query.length >= 2) {
                searchTimeout = setTimeout(function() {
                    showSearchSuggestions(query);
                }, 300);
            } else {
                hideSearchSuggestions();
            }
        });

        // 点击外部关闭建议
        document.addEventListener('click', function(e) {
            if (!searchForm.contains(e.target)) {
                hideSearchSuggestions();
            }
        });
    }

    async function performSearch(query) {
        if (!query) {
            return;
        }

        console.log('搜索:', query);

        // 显示加载状态
        showSearchLoading();

        try {
            // 加载 Pagefind
            const pagefind = await loadPagefind();

            // 执行搜索
            const search = await pagefind.search(query);

            console.log('搜索结果:', search.results.length);

            if (search.results.length === 0) {
                showNoResults(query);
                return;
            }

            // 显示搜索结果
            displaySearchResults(search.results, query);

        } catch (error) {
            console.error('搜索失败:', error);
            showSearchError(error);
        }
    }

    async function loadPagefind() {
        // 动态加载 Pagefind
        if (window.pagefind) {
            return window.pagefind;
        }

        const script = document.createElement('script');
        script.src = '/IFC/RELEASE/IFC4x3/HTML/pagefind/pagefind.js';
        document.head.appendChild(script);

        return new Promise((resolve, reject) => {
            script.onload = async function() {
                await window.pagefind.init();
                resolve(window.pagefind);
            };
            script.onerror = function() {
                reject(new Error('无法加载 Pagefind'));
            };
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
                    <p>抱歉，搜索功能暂时不可用。</p>
                    <p>错误信息: ${escapeHtml(error.message)}</p>
                    <p>请稍后再试，或<a href="/">返回首页</a>。</p>
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
        }

        html += `</div>`;

        if (results.length > maxResults) {
            html += `<p style="color: #666;">...还有 ${results.length - maxResults} 个结果未显示</p>`;
        }

        mainContent.innerHTML = html;
    }

    async function showSearchSuggestions(query) {
        try {
            const pagefind = await loadPagefind();
            const search = await pagefind.search(query);

            if (search.results.length === 0) {
                hideSearchSuggestions();
                return;
            }

            // 创建建议框
            let suggestionsBox = document.getElementById('search-suggestions');
            if (!suggestionsBox) {
                suggestionsBox = document.createElement('div');
                suggestionsBox.id = 'search-suggestions';
                suggestionsBox.style.cssText = `
                    position: absolute;
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    max-height: 300px;
                    overflow-y: auto;
                    z-index: 1000;
                    width: 100%;
                    margin-top: 5px;
                `;

                const searchForm = document.querySelector('form.search');
                searchForm.style.position = 'relative';
                searchForm.appendChild(suggestionsBox);
            }

            let html = '';
            const maxSuggestions = 5;
            for (let i = 0; i < Math.min(search.results.length, maxSuggestions); i++) {
                const result = search.results[i];
                const data = await result.data();

                html += `
                    <a href="${data.url}" style="display: block; padding: 10px; text-decoration: none; color: inherit; border-bottom: 1px solid #eee;">
                        <div style="font-weight: bold;">${escapeHtml(data.meta.title || data.url)}</div>
                        <div style="font-size: 0.85em; color: #666;">${data.url}</div>
                    </a>
                `;
            }

            suggestionsBox.innerHTML = html;
            suggestionsBox.style.display = 'block';

        } catch (error) {
            console.error('建议搜索失败:', error);
            hideSearchSuggestions();
        }
    }

    function hideSearchSuggestions() {
        const suggestionsBox = document.getElementById('search-suggestions');
        if (suggestionsBox) {
            suggestionsBox.style.display = 'none';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
