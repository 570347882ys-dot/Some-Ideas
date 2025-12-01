with tab5:
    # 新增：薪资调整历史趋势分析
    st.subheader("📈 薪资调整历史趋势分析")
    
    if not st.session_state.salary_history:
        st.info("📝 尚未记录任何薪资调整方案。请在左侧边栏点击'记录当前方案'按钮开始记录。")
    else:
        # 显示历史记录概览
        st.success(f"📊 已记录 {len(st.session_state.salary_history)} 次薪资调整方案")
        
        # 准备历史数据
        history_df = pd.DataFrame([
            {
                '调整序号': f"第{item['id']}次",
                '记录时间': item['timestamp'],
                '月度总工资(元)': item['results']['月度总工资'],
                '年度总工资(元)': item['results']['税前年收入'],
                '税前月均工资(元)': item['results']['月度总工资'],
                '税后月均工资(元)': item['results']['月均到手(含年终奖)'],
                '收入转化率(%)': item['results']['收入转化率'] * 100,
                '年终奖计算方式': item['results']['年终奖计算方式'],
                '年终奖包含绩效工资': item['results']['年终奖包含绩效工资']
            }
            for item in st.session_state.salary_history
        ])
        
        # 计算变化率
        if len(history_df) > 1:
            change_rates = []
            for i in range(len(history_df)):
                if i == 0:
                    change_rates.append({
                        '调整序号': f"第{i+1}次",
                        '月度总工资变化率(%)': 0,
                        '年度总工资变化率(%)': 0,
                        '税前月均变化率(%)': 0,
                        '税后月均变化率(%)': 0,
                        '收入转化率变化(百分点)': 0
                    })
                else:
                    prev_row = history_df.iloc[i-1]
                    curr_row = history_df.iloc[i]
                    
                    change_rates.append({
                        '调整序号': f"第{i+1}次",
                        '月度总工资变化率(%)': calculate_change_rate(curr_row['月度总工资(元)'], prev_row['月度总工资(元)']),
                        '年度总工资变化率(%)': calculate_change_rate(curr_row['年度总工资(元)'], prev_row['年度总工资(元)']),
                        '税前月均变化率(%)': calculate_change_rate(curr_row['税前月均工资(元)'], prev_row['税前月均工资(元)']),
                        '税后月均变化率(%)': calculate_change_rate(curr_row['税后月均工资(元)'], prev_row['税后月均工资(元)']),
                        '收入转化率变化(百分点)': curr_row['收入转化率(%)'] - prev_row['收入转化率(%)']
                    })
            
            change_df = pd.DataFrame(change_rates)
        
        # 创建多图表显示
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 历史记录数据表")
            display_df = history_df.copy()
            display_df = display_df[['调整序号', '记录时间', '月度总工资(元)', '年度总工资(元)', 
                                    '税前月均工资(元)', '税后月均工资(元)', '收入转化率(%)', '年终奖计算方式']]
            
            # 格式化显示
            formatted_df = display_df.copy()
            for col in ['月度总工资(元)', '年度总工资(元)', '税前月均工资(元)', '税后月均工资(元)']:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}")
            formatted_df['收入转化率(%)'] = formatted_df['收入转化率(%)'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(formatted_df, use_container_width=True, hide_index=True)
        
        with col2:
            if len(history_df) > 1:
                st.subheader("📊 变化率分析")
                # 格式化变化率数据
                change_display_df = change_df.copy()
                for col in ['月度总工资变化率(%)', '年度总工资变化率(%)', 
                          '税前月均变化率(%)', '税后月均变化率(%)']:
                    change_display_df[col] = change_display_df[col].apply(
                        lambda x: f"{x:+.1f}%" if x != 0 else "0.0%"
                    )
                change_display_df['收入转化率变化(百分点)'] = change_display_df['收入转化率变化(百分点)'].apply(
                    lambda x: f"{x:+.2f}pp" if x != 0 else "0.00pp"
                )
                
                st.dataframe(change_display_df, use_container_width=True, hide_index=True)
            else:
                st.info("📈 记录至少2次调整方案后，将显示变化率分析")
        
        # 绘制历史趋势图 - 优化版本
        st.subheader("📈 薪资调整历史趋势图")
        
        # 计算数据范围，用于统一格线
        min_monthly = history_df['月度总工资(元)'].min()
        max_monthly = history_df['月度总工资(元)'].max()
        min_annual = history_df['年度总工资(元)'].min()
        max_annual = history_df['年度总工资(元)'].max()
        min_monthly_after_tax = history_df['税后月均工资(元)'].min()
        max_monthly_after_tax = history_df['税后月均工资(元)'].max()
        min_conversion = history_df['收入转化率(%)'].min()
        max_conversion = history_df['收入转化率(%)'].max()
        
        # 标准化格线：使用5个均匀分布的刻度
        tick_count = 5
        
        # 为每个指标计算均匀分布的刻度
        monthly_ticks = np.linspace(min_monthly, max_monthly, tick_count)
        annual_ticks = np.linspace(min_annual, max_annual, tick_count)
        after_tax_ticks = np.linspace(min_monthly_after_tax, max_monthly_after_tax, tick_count)
        conversion_ticks = np.linspace(min_conversion, max_conversion, tick_count)
        
        fig_history = go.Figure()
        
        # 添加多条曲线
        fig_history.add_trace(go.Scatter(
            x=history_df['调整序号'],
            y=history_df['月度总工资(元)'],
            mode='lines+markers',
            name='月度总工资',
            line=dict(color='#4CAF50', width=3),
            marker=dict(size=8),
            yaxis='y',
            hovertemplate='<b>月度总工资</b><br>调整: %{x}<br>金额: %{y:,.0f}元<extra></extra>'
        ))
        
        fig_history.add_trace(go.Scatter(
            x=history_df['调整序号'],
            y=history_df['年度总工资(元)'],
            mode='lines+markers',
            name='年度总工资',
            line=dict(color='#2196F3', width=3, dash='dash'),
            marker=dict(size=8),
            yaxis='y2',
            hovertemplate='<b>年度总工资</b><br>调整: %{x}<br>金额: %{y:,.0f}元<extra></extra>'
        ))
        
        fig_history.add_trace(go.Scatter(
            x=history_df['调整序号'],
            y=history_df['税后月均工资(元)'],
            mode='lines+markers',
            name='税后月均工资',
            line=dict(color='#FF9800', width=3, dash='dot'),
            marker=dict(size=8),
            yaxis='y3',
            hovertemplate='<b>税后月均工资</b><br>调整: %{x}<br>金额: %{y:,.0f}元<extra></extra>'
        ))
        
        fig_history.add_trace(go.Scatter(
            x=history_df['调整序号'],
            y=history_df['收入转化率(%)'],
            mode='lines+markers',
            name='收入转化率',
            line=dict(color='#9C27B0', width=3, dash='dashdot'),
            marker=dict(size=8),
            yaxis='y4',
            hovertemplate='<b>收入转化率</b><br>调整: %{x}<br>转化率: %{y:.1f}%<extra></extra>'
        ))
        
        # 更新布局 - 优化格线显示
        fig_history.update_layout(
            title=dict(
                text='薪资调整历史趋势分析',
                font=dict(size=20, color='#2C3E50'),
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title="调整序号",
                tickmode='array',
                tickvals=history_df['调整序号'],
                ticktext=history_df['调整序号'],
                gridcolor='rgba(0,0,0,0.05)',
                showgrid=True,
                gridwidth=1
            ),
            yaxis=dict(
                title="月度总工资 (元)",
                title_font=dict(color='#4CAF50', size=12),
                tickfont=dict(color='#4CAF50', size=10),
                tickmode='array',
                tickvals=monthly_ticks,
                ticktext=[f'{tick:,.0f}' for tick in monthly_ticks],
                gridcolor='rgba(0,0,0,0.05)',
                showgrid=True,
                gridwidth=1,
                zeroline=False
            ),
            yaxis2=dict(
                title="年度总工资 (元)",
                title_font=dict(color='#2196F3', size=12),
                tickfont=dict(color='#2196F3', size=10),
                anchor="x",
                overlaying="y",
                side="right",
                position=0.15,
                tickmode='array',
                tickvals=annual_ticks,
                ticktext=[f'{tick:,.0f}' for tick in annual_ticks],
                gridcolor='rgba(0,0,0,0.03)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            yaxis3=dict(
                title="税后月均工资 (元)",
                title_font=dict(color='#FF9800', size=12),
                tickfont=dict(color='#FF9800', size=10),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.35,
                tickmode='array',
                tickvals=after_tax_ticks,
                ticktext=[f'{tick:,.0f}' for tick in after_tax_ticks],
                gridcolor='rgba(0,0,0,0.02)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            yaxis4=dict(
                title="收入转化率 (%)",
                title_font=dict(color='#9C27B0', size=12),
                tickfont=dict(color='#9C27B0', size=10),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.55,
                tickmode='array',
                tickvals=conversion_ticks,
                ticktext=[f'{tick:.1f}' for tick in conversion_ticks],
                gridcolor='rgba(0,0,0,0.02)',
                showgrid=True,
                gridwidth=0.5,
                zeroline=False
            ),
            hovermode="x unified",
            template=chart_theme,
            height=chart_height,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="rgba(0,0,0,0.1)",
                borderwidth=1
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=80, b=80, l=80, r=100)
        )
        
        # 添加水平参考线（主要网格线）
        for i, tick in enumerate(monthly_ticks):
            if i > 0:  # 跳过第一个，避免与x轴重叠
                fig_history.add_hline(
                    y=tick,
                    line_dash="solid",
                    line_color="rgba(0,0,0,0.05)",
                    line_width=1,
                    opacity=0.3
                )
        
        st.plotly_chart(fig_history, use_container_width=True)
        
        # 绘制变化率图表 - 优化版本
        if len(history_df) > 1:
            st.subheader("📈 变化率趋势图")
            
            # 只从第二次开始有变化率
            change_indicators = ['月度总工资变化率(%)', '年度总工资变化率(%)', 
                               '税前月均变化率(%)', '税后月均变化率(%)']
            
            colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']
            
            # 计算变化率数据的范围
            change_min = float('inf')
            change_max = float('-inf')
            
            for indicator in change_indicators:
                values = change_df[indicator].iloc[1:].values
                change_min = min(change_min, np.min(values))
                change_max = max(change_max, np.max(values))
            
            # 计算收入转化率变化范围
            conversion_values = change_df['收入转化率变化(百分点)'].iloc[1:].values
            conversion_min = np.min(conversion_values)
            conversion_max = np.max(conversion_values)
            
            # 统一两个y轴的范围，使格线对齐
            overall_min = min(change_min, conversion_min)
            overall_max = max(change_max, conversion_max)
            
            # 扩展范围，确保包含0点（如果有正负变化）
            if overall_min > 0:
                overall_min = -overall_max * 0.1  # 向下扩展10%
            if overall_max < 0:
                overall_max = -overall_min * 0.1  # 向上扩展10%
            
            # 确保对称性，使图表更美观
            abs_max = max(abs(overall_min), abs(overall_max))
            overall_min = -abs_max * 1.1  # 扩展10%
            overall_max = abs_max * 1.1    # 扩展10%
            
            # 创建均匀分布的刻度
            tick_count_change = 7  # 使用7个刻度，包括0点
            change_ticks = np.linspace(overall_min, overall_max, tick_count_change)
            
            # 创建柱状图
            fig_change = go.Figure()
            
            # 获取x轴值（跳过第一次）
            x_values = change_df['调整序号'].iloc[1:]
            
            # 添加柱状图（变化率）
            for i, indicator in enumerate(change_indicators):
                y_values = change_df[indicator].iloc[1:].values
                
                # 为正值和负值设置不同颜色
                positive_mask = y_values >= 0
                negative_mask = y_values < 0
                
                if np.any(positive_mask):
                    fig_change.add_trace(go.Bar(
                        x=x_values[positive_mask],
                        y=y_values[positive_mask],
                        name=indicator.replace('变化率(%)', '') + '(+)',
                        marker_color=colors[i],
                        text=[f"{y:+.1f}%" for y in y_values[positive_mask]],
                        textposition='outside',
                        hovertemplate=f'<b>{indicator.replace("变化率(%)", "")}</b><br>调整: %{{x}}<br>变化率: %{{y:+.1f}}%<extra></extra>',
                        showlegend=False  # 不在图例中显示正负分开的条目
                    ))
                
                if np.any(negative_mask):
                    fig_change.add_trace(go.Bar(
                        x=x_values[negative_mask],
                        y=y_values[negative_mask],
                        name=indicator.replace('变化率(%)', '') + '(-)',
                        marker_color=colors[i],
                        marker_pattern_shape="/",  # 添加斜线图案区分负值
                        text=[f"{y:+.1f}%" for y in y_values[negative_mask]],
                        textposition='outside',
                        hovertemplate=f'<b>{indicator.replace("变化率(%)", "")}</b><br>调整: %{{x}}<br>变化率: %{{y:+.1f}}%<extra></extra>',
                        showlegend=False  # 不在图例中显示正负分开的条目
                    ))
            
            # 添加线图（收入转化率变化）
            y_values_conversion = change_df['收入转化率变化(百分点)'].iloc[1:].values
            
            fig_change.add_trace(go.Scatter(
                x=x_values,
                y=y_values_conversion,
                mode='lines+markers',
                name='收入转化率变化',
                line=dict(color='#E91E63', width=3),
                marker=dict(size=8),
                yaxis='y2',
                text=[f"{y:+.2f}pp" for y in y_values_conversion],
                textposition='top center',
                hovertemplate='<b>收入转化率变化</b><br>调整: %{x}<br>变化: %{y:+.2f}pp<extra></extra>'
            ))
            
            # 更新布局 - 优化格线显示
            fig_change.update_layout(
                title=dict(
                    text='各指标变化率趋势',
                    font=dict(size=18, color='#2C3E50'),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(
                    title="调整序号",
                    tickmode='array',
                    tickvals=x_values,
                    ticktext=x_values,
                    gridcolor='rgba(0,0,0,0.05)',
                    showgrid=True,
                    gridwidth=1
                ),
                yaxis=dict(
                    title="变化率 (%)",
                    tickmode='array',
                    tickvals=change_ticks,
                    ticktext=[f'{tick:+.1f}' for tick in change_ticks],
                    range=[overall_min, overall_max],
                    gridcolor='rgba(0,0,0,0.05)',
                    showgrid=True,
                    gridwidth=1,
                    zeroline=True,
                    zerolinecolor='rgba(0,0,0,0.2)',
                    zerolinewidth=1
                ),
                yaxis2=dict(
                    title="收入转化率变化 (百分点)",
                    overlaying="y",
                    side="right",
                    tickmode='array',
                    tickvals=change_ticks,
                    ticktext=[f'{tick:+.2f}' for tick in change_ticks],
                    range=[overall_min, overall_max],
                    gridcolor='rgba(0,0,0,0.03)',
                    showgrid=True,
                    gridwidth=0.5,
                    zeroline=True,
                    zerolinecolor='rgba(0,0,0,0.2)',
                    zerolinewidth=1
                ),
                barmode='group',
                template=chart_theme,
                height=400,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="rgba(0,0,0,0.1)",
                    borderwidth=1
                ),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # 添加水平网格线（均匀分布）
            for tick in change_ticks:
                fig_change.add_hline(
                    y=tick,
                    line_dash="solid",
                    line_color="rgba(0,0,0,0.05)",
                    line_width=1,
                    opacity=0.3
                )
            
            # 添加0线强调
            fig_change.add_hline(
                y=0,
                line_dash="solid",
                line_color="rgba(0,0,0,0.3)",
                line_width=1.5,
                opacity=0.5
            )
            
            # 添加图例说明
            fig_change.add_annotation(
                x=0.02,
                y=1.05,
                xref="paper",
                yref="paper",
                text="💡 柱状图: 各指标变化率 | 线图: 收入转化率变化",
                showarrow=False,
                font=dict(size=10, color='#7F8C8D'),
                bgcolor="rgba(255, 255, 255, 0.7)",
                bordercolor="#DDD",
                borderwidth=1,
                borderpad=4
            )
            
            st.plotly_chart(fig_change, use_container_width=True)
        
        # 显示最佳方案
        if len(history_df) > 1:
            st.subheader("🏆 最佳方案分析")
            
            # 找出税后月均工资最高的方案
            best_monthly_idx = history_df['税后月均工资(元)'].idxmax()
            best_monthly = history_df.iloc[best_monthly_idx]
            
            # 找出收入转化率最高的方案
            best_conversion_idx = history_df['收入转化率(%)'].idxmax()
            best_conversion = history_df.iloc[best_conversion_idx]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success(f"""
                **最佳税后收入方案**：
                - 🥇 **第{best_monthly_idx+1}次调整**
                - 💰 **税后月均工资**: {best_monthly['税后月均工资(元)']:,.0f}元
                - 📊 **月度总工资**: {best_monthly['月度总工资(元)']:,.0f}元
                - 🏦 **年度总工资**: {best_monthly['年度总工资(元)']:,.0f}元
                - 📈 **收入转化率**: {best_monthly['收入转化率(%)']:.1f}%
                - ⏰ **记录时间**: {best_monthly['记录时间']}
                """)
            
            with col2:
                st.info(f"""
                **最佳转化率方案**：
                - 🥈 **第{best_conversion_idx+1}次调整**
                - 📈 **收入转化率**: {best_conversion['收入转化率(%)']:.1f}%
                - 💰 **税后月均工资**: {best_conversion['税后月均工资(元)']:,.0f}元
                - 📊 **月度总工资**: {best_conversion['月度总工资(元)']:,.0f}元
                - 🏦 **年度总工资**: {best_conversion['年度总工资(元)']:,.0f}元
                - ⏰ **记录时间**: {best_conversion['记录时间']}
                """)
