#include<bits/stdc++.h>
using namespace std;


struct Node{
    int label=-1;
    int val;
    Node *left = nullptr;
    Node *right = nullptr;

    Node(){
        
    }
};

unordered_map<int, Node*> ndMap;

random_device rd; 
mt19937 gen(rd()); 
uniform_int_distribution<int> val_distr(0, 1e6); 
uniform_real_distribution<double> real_distr(0.0, 1.0);

Node *generate_tree(int N){    
    if(N == 0) return nullptr;
    Node* root = new Node;
    if(N == 1){
        return root;
    }
    int min_val = 0;
    int max_val = N-1;
    uniform_int_distribution<int> distr(min_val, max_val); 

    int left_nodes = distr(gen);
    int right_nodes = N - 1 - left_nodes;

    root->left = generate_tree(left_nodes);
    root->right = generate_tree(right_nodes);    
    return root;
}

void recurse_label_tree(vector<int>& labels, int& ptr, Node* root){
    if(!root) return;
    int label = labels[ptr++];
    root->label = label;
    ndMap[label] = root;
    root->val = val_distr(gen);


    recurse_label_tree(labels, ptr, root->left);
    recurse_label_tree(labels, ptr, root->right);
}

void label_tree(Node* root, int N){
    vector<int> label(N-1);
    for(int i=1; i<N; i++){
        label[i-1] = i;
    }
    
    shuffle(label.begin(), label.end(), gen);
    
    root->label = 0;
    root->val = val_distr(gen);
    ndMap[0] = root;

    int ptr = 0;
    recurse_label_tree(label, ptr, root->left);
    recurse_label_tree(label, ptr, root->right);

}

void print_edges(Node* root){
    if(!root) return;
    if(root->left){
        cout << root->label << ' ' << root->left->label << '\n';
        print_edges(root->left);
    }
    if(root->right){
        cout << root->label << ' ' << root->right->label << '\n';
        print_edges(root->right);
    }
    
}

void print_std( int N, int Q){
    cout << N << ' ' << Q <<endl;
    for(int nd=0; nd<N; nd++){
        Node* node = ndMap[nd];
        cout << node->val << ' ';
        if(node->left){
            cout << node->left->label << ' ';
        }
        else{
            cout << -1 << ' ';
        }

        if(node->right){
            cout << node->right->label << ' ';
        }
        else{
            cout << -1 << ' ';
        }
        cout << '\n';
    }
}

void construct_tc(int N, int Q){
    Node *root = generate_tree(N);    
    label_tree(root, N);
    // print_edges(root);
    uniform_int_distribution<int> node_distr(0,N-1);
    print_std(N, Q);

    for(int i=0; i<Q; i++){
        float num_ = real_distr(gen);
        if(num_ < 0.4){
            cout << "L " << node_distr(gen) << endl;
        }
        else if(num_ < 0.8){
            cout << "M " << node_distr(gen) << endl;
        }
        else{
            cout << "D " << node_distr(gen) << endl;
        }
    }

}

int main(int argc, char* argv[]){
    if(argc != 3){
        return 1;
    }

    int N = atoi(argv[1]);
    int Q = atoi(argv[2]);
    construct_tc(N,Q);
    
    
}