import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import io
from config import (
    FINANCIAL_PARAMS,
    EFFECTIVENESS_PARAMS,
    ECONOMIC_VALUES,
    PDF_CONFIG,
)


class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()

    def _create_custom_styles(self):
        """Cria estilos personalizados para o relatório usando config.py"""
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Title"],
            fontSize=PDF_CONFIG["font_sizes"]["title"],
            spaceAfter=30,
            textColor=colors.HexColor(PDF_CONFIG["colors"]["title"]),
            alignment=1,
        )

        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=self.styles["Heading2"],
            fontSize=PDF_CONFIG["font_sizes"]["subtitle"],
            spaceAfter=15,
            textColor=colors.HexColor(PDF_CONFIG["colors"]["subtitle"]),
            borderWidth=1,
            borderColor=colors.HexColor(PDF_CONFIG["colors"]["title"]),
            backColor=colors.HexColor("#f8f9fa"),
            leftIndent=10,
            rightIndent=10,
            spaceBefore=20,
        )

        return {"title": title_style, "subtitle": subtitle_style}

    def generate_accident_analysis_report(
        self,
        filtered_data,
        top_segments,
    ):
        """Gera relatório completo de análise de acidentes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        story = []

        # Título e cabeçalho
        story.append(
            Paragraph(
                "RELATÓRIO DE ANÁLISE DE ACIDENTES RODOVIÁRIOS",
                self.custom_styles["title"],
            )
        )
        story.append(
            Paragraph(
                "Projeto Iluminar para Proteger", self.styles["Heading3"]
            )
        )
        story.append(
            Paragraph(
                f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 20))

        # Resumo executivo
        story.append(
            Paragraph("RESUMO EXECUTIVO", self.custom_styles["subtitle"])
        )
        total_acidentes = len(filtered_data)
        acidentes_noturnos = len(
            filtered_data[filtered_data["fase_dia"] == "noturno"]
        )
        perc_noturnos = (
            (acidentes_noturnos / total_acidentes) * 100
            if total_acidentes > 0
            else 0
        )
        total_mortos = filtered_data["mortos"].sum()
        total_feridos = filtered_data["total_feridos"].sum()
        resumo_text = f"""
         Este relatório analisa {total_acidentes:,} acidentes rodoviários, identificando padrões críticos para a
         implementação de iluminação solar.<br/>
         <b>Principais Indicadores:</b><br/>
         • Total de Acidentes: {total_acidentes:,}<br/>
         • Acidentes Noturnos: {acidentes_noturnos:,} ({perc_noturnos:.1f}%)<br/>
         • Total de Mortos: {int(total_mortos):,}<br/>
         • Total de Feridos: {int(total_feridos):,}<br/>
         • Trechos Prioritários Identificados: {len(top_segments)}<br/>
        """
        story.append(Paragraph(resumo_text, self.styles["Normal"]))
        story.append(Spacer(1, 20))

        # Análise por período do dia
        story.append(
            Paragraph(
                "ANÁLISE POR PERÍODO DO DIA", self.custom_styles["subtitle"]
            )
        )
        data_com_fatais = filtered_data.copy()
        data_com_fatais["acidente_fatal"] = data_com_fatais["mortos"] > 0
        fatais_por_periodo = data_com_fatais.groupby("fase_dia")[
            "acidente_fatal"
        ].sum()
        acidentes_fatais_noturnos = int(fatais_por_periodo.get("noturno", 0))
        acidentes_fatais_diurnos = int(fatais_por_periodo.get("diurno", 0))
        periodo_stats = (
            filtered_data.groupby("fase_dia")
            .agg({"mortos": ["count", "mean"]})
            .round(2)
        )
        periodo_text = "<b>Comparação Noturno vs Diurno:</b><br/>"
        if (
            "noturno" in periodo_stats.index
            and "diurno" in periodo_stats.index
        ):
            acidentes_not = periodo_stats.loc["noturno", ("mortos", "count")]
            acidentes_dia = periodo_stats.loc["diurno", ("mortos", "count")]
            mortalidade_noturna = periodo_stats.loc[
                "noturno", ("mortos", "mean")
            ]
            mortalidade_diurna = periodo_stats.loc[
                "diurno", ("mortos", "mean")
            ]
            periodo_text += f"""
             • Acidentes Noturnos: {int(acidentes_not):,} (dos quais <b>{acidentes_fatais_noturnos:,} foram fatais</b>)<br/>
             • Acidentes Diurnos: {int(acidentes_dia):,} (dos quais <b>{acidentes_fatais_diurnos:,} foram fatais</b>)<br/><br/>
             • Letalidade Noturna: {mortalidade_noturna:.2f} mortos/acidente<br/>
             • Letalidade Diurna: {mortalidade_diurna:.2f} mortos/acidente<br/>
             • Fator de Risco Noturno: {(mortalidade_noturna/mortalidade_diurna if mortalidade_diurna > 0 else 1):.1f}x mais letal<br/>
            """
        story.append(Paragraph(periodo_text, self.styles["Normal"]))
        story.append(Spacer(1, 15))

        # Top trechos críticos
        story.append(
            Paragraph(
                "TRECHOS PRIORITÁRIOS PARA ILUMINAÇÃO",
                self.custom_styles["subtitle"],
            )
        )
        if not top_segments.empty:
            table_data = [
                [
                    "Ranking",
                    "Trecho (BR-KM-UF)",
                    "Acidentes",
                    "Mortos",
                    "Feridos",
                    "Score",
                    "ROI 10 anos",
                ]
            ]
            for i, (_, row) in enumerate(top_segments.head(10).iterrows()):
                table_data.append(
                    [
                        str(i + 1),
                        str(row.get("trecho", "N/A")),
                        str(row.get("n_acidentes", 0)),
                        str(int(row.get("mortos", 0))),
                        str(int(row.get("total_feridos", 0))),
                        str(int(row.get("score_prioridade", 0))),
                        f"{row.get('roi_10anos', 0):.1f}%",
                    ]
                )
            table = Table(
                table_data,
                colWidths=[
                    0.8 * inch,
                    2.5 * inch,
                    0.8 * inch,
                    0.7 * inch,
                    0.7 * inch,
                    0.8 * inch,
                    1.0 * inch,
                ],
            )
            table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#1f77b4"),
                        ),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 20))

        # Análise de ROI
        story.append(
            Paragraph(
                "ANÁLISE DE RETORNO SOBRE INVESTIMENTO",
                self.custom_styles["subtitle"],
            )
        )
        if not top_segments.empty:
            top_100 = top_segments.head(100)

            vitimas_evitadas_ano = (
                top_100["acidentes_evitados_ano"].sum()
                if "acidentes_evitados_ano" in top_100.columns
                else 0
            )

            investimento_total = (
                top_100["investimento_trecho"].sum()
                if "investimento_trecho" in top_100.columns
                else 0
            )
            reducao = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]
            economia_mortos = (
                top_100["mortos"].sum() * reducao
            ) * ECONOMIC_VALUES["valor_vida_estatistica"]
            economia_graves = (
                top_100["feridos_graves"].sum() * reducao
            ) * ECONOMIC_VALUES["custo_medio_acidente_grave"]
            economia_leves = (
                top_100["feridos_leves"].sum() * reducao
            ) * ECONOMIC_VALUES["custo_medio_acidente_leve"]
            economia_anual = economia_mortos + economia_graves + economia_leves
            payback_medio_anos = top_100["payback_anos"].mean()
            payback_str = (
                f"{payback_medio_anos * 365:.1f} dias"
                if payback_medio_anos < 1
                else f"{payback_medio_anos:.2f} anos"
            )
            roi_medio_10_anos = top_100["roi_10anos"].mean()

            roi_text = f"""
            <b>Análise Financeira - Top {len(top_100)} Trechos Prioritários:</b><br/>
            • Investimento Total: R$ {investimento_total:,.2f}<br/>
            • Vítimas Evitadas por Ano: {vitimas_evitadas_ano:.1f}<br/>
            • <b>Economia Anual Total Estimada: R$ {economia_anual:,.2f}</b><br/>
            <i><font size=8>    - Com Vidas Salvas: R$ {economia_mortos:,.2f}</font></i><br/>
            <i><font size=8>    - Com Fer. Graves Evitados: R$ {economia_graves:,.2f}</font></i><br/>
            <i><font size=8>    - Com Fer. Leves Evitados: R$ {economia_leves:,.2f}</font></i><br/>
            • Payback Médio: {payback_str}<br/>
            • ROI em 10 anos: {roi_medio_10_anos:,.1f}%<br/><br/>
            <b>Premissas do Cálculo:</b><br/>
            • Custo de instalação por poste: R$ {FINANCIAL_PARAMS["custo_poste_solar"]:,.2f}<br/>
            • Redução esperada de acidentes noturnos: {EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]:.0%}<br/>
            • Valor por vida salva (fatalidade): R$ {ECONOMIC_VALUES["valor_vida_estatistica"]:,.2f}<br/>
            • Custo médio por ferido grave: R$ {ECONOMIC_VALUES["custo_medio_acidente_grave"]:,.2f}<br/>
            • Custo médio por ferido leve: R$ {ECONOMIC_VALUES["custo_medio_acidente_leve"]:,.2f}<br/>
            • Vida útil do sistema: {FINANCIAL_PARAMS["vida_util_anos"]} anos<br/>
            """
            story.append(Paragraph(roi_text, self.styles["Normal"]))
            story.append(Spacer(1, 20))

            # Recomendações
            story.append(
                Paragraph(
                    "RECOMENDAÇÕES ESTRATÉGICAS",
                    self.custom_styles["subtitle"],
                )
            )
            recomendacoes_text = """
             <b>1. Implementação Imediata:</b><br/> • Iniciar projeto piloto nos 20 trechos mais críticos<br/> • Estabelecer parcerias com concessionárias de rodovias<br/> • Criar cronograma de implantação por fases<br/>
             <b>2. Monitoramento e Avaliação:</b><br/> • Implementar sistema de monitoramento contínuo<br/> • Avaliar efetividade após 12 meses de operação<br/> • Ajustar metodologia baseada em resultados<br/>
             <b>3. Expansão do Programa:</b><br/> • Expandir para os próximos 100 trechos prioritários<br/> • Buscar financiamento adicional baseado em resultados<br/> • Replicar modelo para outras regiões do país<br/>
             <b>4. Inovação Tecnológica:</b><br/> • Integrar sensores de movimento para otimização energética<br/> • Implementar sistema de telemetria para manutenção preditiva<br/> • Desenvolver algoritmos de IA para predição de riscos<br/>
            """
            story.append(Paragraph(recomendacoes_text, self.styles["Normal"]))
            story.append(Spacer(1, 15))

            # Conclusão
            story.append(
                Paragraph("CONCLUSÃO", self.custom_styles["subtitle"])
            )
            reducao = EFFECTIVENESS_PARAMS["reducao_acidentes_noturnos"]
            vidas_salvas_ano = top_100["mortos"].sum() * reducao
            feridos_graves_evitados = top_100["feridos_graves"].sum() * reducao
            feridos_leves_evitados = top_100["feridos_leves"].sum() * reducao
            conclusao_text = f"""
             A análise dos dados de acidentes rodoviários demonstra claramente a correlação entre a falta de iluminação e o aumento da severidade dos acidentes noturnos. Com {perc_noturnos:.1f}% dos acidentes ocorrendo no período noturno e apresentando maior letalidade, a implementação de iluminação solar nos trechos prioritários identificados representa uma oportunidade concreta de salvar vidas e reduzir custos sociais.
             O projeto "Iluminar para Proteger" não apenas demonstra o poder da análise de dados para resolver problemas reais da sociedade, mas também exemplifica como a tecnologia pode ser aplicada de forma responsável para gerar impacto social positivo. <b>A implementação das recomendações deste relatório tem o potencial de salvar {int(vidas_salvas_ano)} vidas, evitar {int(feridos_graves_evitados)} ferimentos graves e {int(feridos_leves_evitados)} ferimentos leves por ano, representando um investimento de alto retorno social e econômico.</b>
            """
            story.append(Paragraph(conclusao_text, self.styles["Normal"]))

        # Rodapé
        story.append(Spacer(1, 15))
        story.append(
            Paragraph(
                "Relatório gerado pelo Sistema Iluminar para Proteger",
                self.styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"Data: {datetime.now().strftime('%d de %B de %Y')}",
                self.styles["Normal"],
            )
        )

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_temporal_trend_chart(self, data):
        """Cria gráfico de tendência temporal usando matplotlib"""
        if (
            "ano" not in data.columns
            or "fase_dia" not in data.columns
            or data["ano"].empty
        ):
            return Spacer(1, 0)
        plt.style.use("seaborn-v0_8-whitegrid")
        plt.figure(figsize=(10, 5))
        tendencia = (
            data.groupby(["ano", "fase_dia"])
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )
        anos = tendencia.index.astype(str)
        if "noturno" in tendencia.columns:
            plt.plot(
                anos,
                tendencia["noturno"],
                marker="o",
                linestyle="-",
                label="Acidentes Noturnos",
                color="#1f77b4",
            )
        if "diurno" in tendencia.columns:
            plt.plot(
                anos,
                tendencia["diurno"],
                marker="s",
                linestyle="--",
                label="Acidentes Diurnos",
                color="#ff7f0e",
            )
        anos_presentes = sorted(data["ano"].dropna().unique())
        year_range_str = (
            f"({'-'.join(str(int(a)) for a in anos_presentes)})"
            if len(anos_presentes) > 1
            else f"({int(anos_presentes[0])})"
        )
        plt.title(
            f"Evolução Anual de Acidentes {year_range_str}",
            fontsize=16,
            fontweight="bold",
        )
        plt.xlabel("Ano", fontsize=12)
        plt.ylabel("Número de Acidentes", fontsize=12)
        plt.legend()
        plt.tight_layout()
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", dpi=200)
        img_buffer.seek(0)
        plt.close()
        return Image(img_buffer, width=7 * inch, height=3.5 * inch)
