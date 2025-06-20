import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import threading
import time
from typing import Dict, List
import json
import logging
import os

from core.sentiment import TicketProcessor
from streaming.kafka_client import DemoMessageGenerator
from streaming.data_flow_manager import DataFlowManager
from ai.response_generator import AIResponseGenerator, ResponseTemplateManager

# Configure logging for Stream Lineage tracking
logger = logging.getLogger(__name__)

class SentimentDashboard:
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.ticket_processor = TicketProcessor()
        self.message_generator = DemoMessageGenerator()
        self.ai_generator = AIResponseGenerator(demo_mode)
        self.template_manager = ResponseTemplateManager()
        self.data_flow_manager = DataFlowManager(demo_mode)
        self.is_running = False
        self.processed_tickets = []
        self.messages_sent = 0  # Track for Stream Lineage visibility
        
        # Log initialization for Stream Lineage tracking
        logger.info("🎭 Gradio Sentiment Dashboard initialized")
        logger.info(f"   Mode: {'Demo' if demo_mode else 'Production'}")
        logger.info(f"   Client ID: gradio-sentiment-producer/consumer")
        logger.info("   📊 This app will appear in Confluent Stream Lineage when producing/consuming messages")
        
    def create_dashboard(self):
        with gr.Blocks(title="Real-Time Customer Sentiment Dashboard", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🎯 Real-Time Customer Sentiment & Support Optimizer")
            gr.Markdown("**Demo**: Simulating live chat/support tickets with AI-powered sentiment analysis and response generation")
            
            # Stream Lineage visibility info
            lineage_mode = "🔗 **Stream Lineage**: Live Kafka activity visible in Confluent Cloud" if not self.demo_mode else "🎭 **Demo Mode**: Kafka simulation active"
            gr.Markdown(f"{lineage_mode} | Client ID: `gradio-sentiment-producer/consumer`")
            
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("## 📊 Live Metrics")
                    
                    with gr.Row():
                        total_tickets = gr.Number(label="Total Tickets", value=0, interactive=False)
                        escalation_rate = gr.Number(label="Escalation Rate (%)", value=0, interactive=False)
                        avg_sentiment = gr.Number(label="Avg Sentiment", value=0, interactive=False)
                    
                    sentiment_chart = gr.Plot(label="Sentiment Distribution")
                    priority_chart = gr.Plot(label="Priority Distribution")
                    
                with gr.Column(scale=1):
                    gr.Markdown("## 🚨 Live Ticket Stream")
                    
                    with gr.Row():
                        start_btn = gr.Button("▶️ Start Demo", variant="primary")
                        stop_btn = gr.Button("⏹️ Stop Demo", variant="secondary")
                    
                    live_ticket = gr.JSON(label="Latest Ticket", value={})
                    sentiment_result = gr.JSON(label="Sentiment Analysis", value={})
                    ai_response = gr.Textbox(label="AI Generated Response", lines=4, interactive=False)
            
            with gr.Row():
                gr.Markdown("## 📈 Recent Tickets Timeline")
                tickets_table = gr.Dataframe(
                    headers=["Ticket ID", "Customer", "Sentiment", "Priority", "Escalation", "Timestamp"],
                    datatype=["str", "str", "str", "str", "bool", "str"],
                    interactive=False
                )
            
            with gr.Row():
                gr.Markdown("## 🎛️ Manual Ticket Simulator")
                with gr.Column():
                    customer_message = gr.Textbox(
                        label="Customer Message",
                        placeholder="Enter a customer support message to analyze...",
                        lines=3
                    )
                    with gr.Row():
                        force_escalation = gr.Checkbox(
                            label="🚨 Force Escalation",
                            value=False,
                            info="Override automatic escalation detection"
                        )
                        analyze_btn = gr.Button("🔍 Analyze Message", variant="primary")
                    
                    manual_sentiment = gr.JSON(label="Analysis Result", value={})
                    manual_response = gr.Textbox(label="Generated Response", lines=4, interactive=False)
            
            # Event handlers
            start_btn.click(
                fn=self.start_demo,
                outputs=[start_btn, stop_btn]
            )
            
            stop_btn.click(
                fn=self.stop_demo,
                outputs=[start_btn, stop_btn]
            )
            
            analyze_btn.click(
                fn=self.analyze_manual_message,
                inputs=[customer_message, force_escalation],
                outputs=[manual_sentiment, manual_response]
            )
            
            # Auto-refresh components using timer
            def update_dashboard():
                return self.get_dashboard_update()
            
            # Create timer for auto-refresh (must be inside Blocks context)
            timer = gr.Timer(2.0)
            timer.tick(
                update_dashboard,
                outputs=[
                    total_tickets, escalation_rate, avg_sentiment,
                    sentiment_chart, priority_chart,
                    live_ticket, sentiment_result, ai_response,
                    tickets_table
                ]
            )
        
        return demo
    
    def start_demo(self):
        self.is_running = True
        threading.Thread(target=self._demo_loop, daemon=True).start()
        return gr.Button("▶️ Start Demo", interactive=False), gr.Button("⏹️ Stop Demo", interactive=True)
    
    def stop_demo(self):
        self.is_running = False
        return gr.Button("▶️ Start Demo", interactive=True), gr.Button("⏹️ Stop Demo", interactive=False)
    
    def _demo_loop(self):
        while self.is_running:
            # Generate and process a new ticket
            raw_ticket = self.message_generator.get_next_message()
            raw_ticket['source'] = 'demo_simulator'
            
            processed = self.ticket_processor.process_ticket(raw_ticket)
            ai_result = self.ai_generator.generate_response(processed)
            
            # Send through complete Kafka flow for Stream Lineage visibility
            self.data_flow_manager.process_complete_ticket_flow(
                raw_ticket=raw_ticket,
                processed_ticket=processed,
                ai_response=ai_result
            )
            self.messages_sent += 3  # 3 messages sent (raw, processed, ai_response)
            
            # Log for Stream Lineage tracking
            if self.messages_sent % 10 == 0:  # Log every 10th batch to avoid spam
                logger.info(f"📊 Stream Lineage Activity: {self.messages_sent} messages sent from gradio-sentiment-producer")
                logger.info(f"   🔗 Check Confluent Stream Lineage for 'gradio-sentiment-producer' client")
            
            # Store the processed ticket with AI response for dashboard
            processed["ai_response"] = ai_result["ai_response"]
            processed["response_type"] = ai_result["response_type"]
            processed["source"] = "demo_simulator"
            
            self.processed_tickets.append(processed)
            
            # Keep only last 50 tickets
            if len(self.processed_tickets) > 50:
                self.processed_tickets = self.processed_tickets[-50:]
            
            time.sleep(3)  # Wait 3 seconds between messages
    
    def get_dashboard_update(self):
        data = self.ticket_processor.get_dashboard_data()
        
        # Create charts
        sentiment_chart = self.create_sentiment_chart(data["sentiment_distribution"])
        priority_chart = self.create_priority_chart(data["priority_distribution"])
        
        # Get latest ticket info
        latest_ticket = {}
        latest_sentiment = {}
        latest_response = ""
        
        if self.processed_tickets:
            latest = self.processed_tickets[-1]
            latest_ticket = {
                "ticket_id": latest["ticket_id"],
                "customer_id": latest["customer_id"],
                "message": latest["original_message"][:100] + "..." if len(latest["original_message"]) > 100 else latest["original_message"]
            }
            
            latest_sentiment = {
                "sentiment": latest["sentiment"],
                "polarity": round(latest["polarity"], 3),
                "priority": latest["priority"],
                "needs_escalation": latest["needs_escalation"]
            }
            
            latest_response = latest.get("ai_response", "")
        
        # Create tickets table
        table_data = []
        for ticket in self.processed_tickets[-10:]:  # Last 10 tickets
            table_data.append([
                ticket["ticket_id"],
                ticket["customer_id"],
                ticket["sentiment"],
                ticket["priority"],
                ticket["needs_escalation"],
                ticket["timestamp"][:19]  # Remove microseconds from timestamp
            ])
        
        # Calculate metrics
        total = len(self.processed_tickets)
        escalation_count = sum(1 for t in self.processed_tickets if t["needs_escalation"])
        escalation_rate = (escalation_count / total * 100) if total > 0 else 0
        avg_sentiment = sum(t["polarity"] for t in self.processed_tickets) / total if total > 0 else 0
        
        return (
            total,
            round(escalation_rate, 1),
            round(avg_sentiment, 3),
            sentiment_chart,
            priority_chart,
            latest_ticket,
            latest_sentiment,
            latest_response,
            table_data
        )
    
    def create_sentiment_chart(self, sentiment_data: Dict):
        labels = list(sentiment_data.keys())
        values = list(sentiment_data.values())
        colors = ['#2E8B57', '#DC143C', '#4682B4']  # Green, Red, Blue
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            title="Sentiment Distribution",
            showlegend=True,
            height=300
        )
        
        return fig
    
    def create_priority_chart(self, priority_data: Dict):
        labels = list(priority_data.keys())
        values = list(priority_data.values())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']  # Red, Teal, Blue
        
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color=colors
        )])
        
        fig.update_layout(
            title="Priority Distribution",
            xaxis_title="Priority Level",
            yaxis_title="Count",
            height=300
        )
        
        return fig
    
    def analyze_manual_message(self, message: str, force_escalation: bool = False):
        if not message.strip():
            return {}, ""
        
        # Create a manual ticket
        raw_ticket = {
            "ticket_id": f"MANUAL_{int(time.time())}",
            "customer_id": "MANUAL_USER",
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "manual_simulator"
        }
        
        # Process the ticket
        processed = self.ticket_processor.process_ticket(raw_ticket)
        
        # Apply manual escalation override if checked
        if force_escalation:
            processed["needs_escalation"] = True
            processed["priority"] = "high"
            processed["escalation_score"] = 1.0
            processed["manual_escalation"] = True
        
        ai_result = self.ai_generator.generate_response(processed)
        
        # 🚀 Send through complete Kafka flow for manual tickets (Stream Lineage visibility)
        self.data_flow_manager.process_complete_ticket_flow(
            raw_ticket=raw_ticket,
            processed_ticket=processed,
            ai_response=ai_result
        )
        self.messages_sent += 3  # 3 messages sent (raw, processed, ai_response)
        
        # Log manual message for Stream Lineage tracking
        logger.info(f"📊 Manual Message Processed: Sent to Kafka topics via gradio-sentiment-producer")
        logger.info(f"   Total messages from Gradio: {self.messages_sent}")
        logger.info(f"   🔗 Visible in Confluent Stream Lineage as 'gradio-sentiment-producer'")
        
        # Store the processed ticket with AI response for dashboard
        processed["ai_response"] = ai_result["ai_response"]
        processed["response_type"] = ai_result["response_type"]
        processed["source"] = "manual_simulator"
        
        # Add to processed tickets list for dashboard display
        self.processed_tickets.append(processed)
        
        # Keep only last 50 tickets
        if len(self.processed_tickets) > 50:
            self.processed_tickets = self.processed_tickets[-50:]
        
        # Return analysis and response
        analysis = {
            "ticket_id": raw_ticket["ticket_id"],
            "sentiment": processed["sentiment"],
            "polarity": round(processed["polarity"], 3),
            "subjectivity": round(processed["subjectivity"], 3),
            "priority": processed["priority"],
            "needs_escalation": processed["needs_escalation"],
            "escalation_score": round(processed["escalation_score"], 3),
            "urgency_score": round(processed["urgency_score"], 3),
            "manual_escalation": processed.get("manual_escalation", False),
            "escalation_reason": "🚨 Manual override" if force_escalation else "🤖 Automatic detection",
            "kafka_sent": "✅ Sent to all Kafka topics" if not self.demo_mode else "🎭 Demo mode - would send to Kafka"
        }
        
        return analysis, ai_result["ai_response"]

def launch_dashboard(demo_mode: bool = True, port: int = 7860):
    dashboard = SentimentDashboard(demo_mode=demo_mode)
    app = dashboard.create_dashboard()
    
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True
    )