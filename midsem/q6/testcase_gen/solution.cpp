#include<bits/stdc++.h>
using namespace std;


void mirror(vector<vector<int>>& adj, int nd){
    if(nd==-1) return;
    swap(adj[nd][0], adj[nd][1]);
    mirror(adj, adj[nd][0]);
    mirror(adj, adj[nd][1]);
}

void levelOrder(vector<vector<int>> & adj, int nd, vector<int>& val){
    queue<int> q;
    q.push(nd);
    while(!q.empty()){
        int curr = q.front();
        q.pop();
        cout << val[curr] << ' ';
        for(auto c: adj[curr]){
            if(c!=-1) q.push(c);
        }
    }
    cout << '\n';
}

void dst(vector<vector<int>> & adj, int nd, vector<int>& val){
    if(nd==-1) return;
    int sm = 0;
    for(auto c: adj[nd]){
        if(c!=-1) {
            sm += val[c];
            dst(adj, c, val);
            sm += val[c];
        }
    }
    val[nd] = sm;
}


int main(){
    int n,q;
    cin >> n >> q;

    vector<int> par(n);
    vector<vector<int>> adj(n);
    vector<int> vals(n);
    for(int i=0; i<n; i++){
        int val, c1, c2;
        cin >> val >> c1 >> c2;
        
        vals[i] = val;
        if(c1!=-1){
            par[c1] = i;
        }
        if(c2!=-1){
            par[c2] = i;
        }        
        adj[i].push_back(c1);
        adj[i].push_back(c2);
    }

    while(q--){
        char qt;
        int u;
        cin >> qt >> u;
        if(qt=='D'){
            dst(adj, u, vals);
        }
        else if(qt == 'M'){
            mirror(adj, u);
        }
        else{
            levelOrder(adj, u, vals);
        }
    }
}