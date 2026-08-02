package com.demo;

import com.demo.BankAccount;
import org.junit.Test;

public class BankAccount_deposit_Dbl_Test_Boundary_5 {


    @Test(expected = IllegalArgumentException.class)
    public void depositZeroAmountThrowsIllegalArgumentException() {
        BankAccount account = new BankAccount("Alice", 100.0);
        account.deposit(0.0);
    }

}
