import { supabase } from '../lib/supabase';
const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

export async function listConversations(userId) {
  if (!userId || userId==='undefined') throw new Error('Missing user_id');
  const {data, error} = await supabase
  .from('conversations')
  .select('conversationid, conversationtitle, updatedat, createdat')
  .eq('userid', userId)
  .order('updatedat', {ascending: false});


  if (error) throw error;

  return {
    conversations: (data || []).map((c) => ({
      conversation_id: c.conversationid,
      title: c.conversationtitle,
      updated_at: c.updatedat,
      created_at: c.createdat,
    })),
  };
}

export async function createConversation(userId) {
  if (!userId) throw new Error('Missing user_id');
  const {data, error} = await supabase
  .from('conversations')
  .insert({
    userid: userId,
    conversationtitle: 'New Conversation',
    conversationdata: [],
  })
  .select()
  .single();
  if (error) throw error;
  return {
    conversation_id: data.conversationid,
    title: data.conversationtitle,
    updated_at: data.updatedat,
    created_at: data.createdat,
  };
}

export async function getConversation(conversationId) {
  if (!conversationId) return null;
  const{data , error} = await supabase
  .from("conversations")
  .select("*")
  .eq("conversationid", conversationId)
  .single();
  if (error) throw error;

  return {
    conversation_id: data.conversationid,
    title: data.conversationtitle,
    messages: data.conversationdata || [],
  };

}


export async function deleteConversation(conversationId) {

  if (!conversationId){
    throw new Error("Missing Conversation ID");
  } 

  const {error} = await supabase
  .from("conversations")
  .delete()
  .eq("conversationid", conversationId);

  if (error) throw error;

  return {
    success: true,
  };

}

export async function sendMessage(conversationId, message) {
  if (!conversationId || !message?.trim()) throw new Error('Missing conversation or message');
  const res = await fetch(`${API_V1}/messages/${encodeURIComponent(conversationId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message.trim() }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to send message');
  return data;
}

